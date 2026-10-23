"""Motor de exercícios do painel: validação, embaralhamento, correção e sorteio dos tipos.

Contrato em DESIGN.md §9. A regra que organiza tudo: o `dados` de um exercício
tem o gabarito e nunca sai do servidor. O navegador recebe o `render`, já
embaralhado, e a correção acontece aqui.
"""
import difflib
import json
import random
import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from japones import audio, dominio, regras

# Os tipos que se respondem e entram no sorteio. O 'explicacao' (23/10/2026) fica fora de propósito:
# não é exercício, é o texto do conteúdo novo antes dos exercícios — sem resposta, placar nem peso.
TIPOS = ("escolha", "achar_erro", "ligar", "ordenar", "completar", "digitar", "conjugar", "ouvir", "producao")
EXPLICACAO = "explicacao"
BLOCOS = ("aquecimento", "novo", "verificacao", "producao", "revisao")
# bloco do exercício -> bloco da tabela `erro` ('novo' é a verificação do conteúdo do dia)
_BLOCO_ERRO = {"aquecimento": "abertura", "novo": "verificacao", "verificacao": "verificacao",
               "producao": "producao", "revisao": "outro"}
# A dica da 2ª tentativa (§9.6) aponta onde olhar ("confira o tempo do verbo"), não explica a regra:
# a explicação vem depois, com a correção. Nos tipos sem correção automática ela não tem como abrir.
DICA_MAX = 200
_SEM_DICA = ("producao", EXPLICACAO)


class ExercicioIn(BaseModel):
    tipo: Literal["escolha", "achar_erro", "ligar", "ordenar", "completar", "digitar", "conjugar", "ouvir",
                  "producao", "explicacao"]
    bloco: Literal["aquecimento", "novo", "verificacao", "producao", "revisao"] | None = Field(
        default=None, description="padrão 'verificacao'; no explicacao, 'novo'")
    enunciado: str | None = Field(default=None, description="a instrução, em português (opcional só no explicacao)")
    dados: dict = Field(description="por tipo, DESIGN §9.2 — com o gabarito")
    explicacao: str | None = Field(default=None, description="a regra, mostrada depois da resposta")
    categoria: str | None = Field(default=None, description="categoria de erro (DESIGN §4.2)")
    regra: str | None = Field(default=None, description="slug da regra do caderno que este exercício revisa (§13)")
    dica_erro: str | None = Field(default=None, description="dica curta para a 2ª tentativa depois de um erro (§9.6)")

    @model_validator(mode="after")
    def _bloco_padrao(self):
        if self.bloco is None:
            self.bloco = "novo" if self.tipo == EXPLICACAO else "verificacao"
        return self


# ------------------------------------------------------------------ texto

_PONTUACAO = re.compile(r"[\s。、.,!?！？・「」]")


def normalizar(texto: str) -> str:
    """NFKC, sem espaço nem pontuação. Katakana e hiragana NÃO se equivalem: trocar é erro."""
    return _PONTUACAO.sub("", unicodedata.normalize("NFKC", texto or ""))


def diff(resposta: str, alvo: str) -> list[dict]:
    """Diff por caractere, do ponto de vista dele: 'faltou' estava no alvo, 'sobrou' ele pôs a mais."""
    a, b = normalizar(resposta), normalizar(alvo)
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            ops.append({"op": "igual", "texto": b[j1:j2]})
        else:
            if i2 > i1:
                ops.append({"op": "sobrou", "texto": a[i1:i2]})
            if j2 > j1:
                ops.append({"op": "faltou", "texto": b[j1:j2]})
    return ops


def _mais_parecida(texto: str, aceitas: list[str]) -> str:
    n = normalizar(texto)
    return max(aceitas, key=lambda x: difflib.SequenceMatcher(None, n, normalizar(x)).ratio())


# ------------------------------------------------------------------ validação

def _lista_str(v, nome, minimo=1):
    if not isinstance(v, list) or len(v) < minimo or not all(isinstance(x, str) and x.strip() for x in v):
        raise ValueError(f"'{nome}' deve ser uma lista de pelo menos {minimo} texto(s) não vazio(s)")
    return v


def validar(ex: ExercicioIn) -> None:
    """Levanta ValueError com a mensagem do que está errado. Chamada antes de gravar."""
    d, t = ex.dados, ex.tipo
    if t != EXPLICACAO and ex.enunciado is None:
        raise ValueError("falta 'enunciado'")
    if ex.dica_erro is not None:
        if t in _SEM_DICA:
            raise ValueError(f"'dica_erro' não vale para {t}: a dica só abre depois de uma correção automática errada")
        if not ex.dica_erro.strip():
            raise ValueError("'dica_erro' é um texto não vazio (ou omita o campo)")
        if len(ex.dica_erro.strip()) > DICA_MAX:
            raise ValueError(f"'dica_erro' tem {len(ex.dica_erro.strip())} caracteres; o máximo é {DICA_MAX} "
                             "(a dica aponta onde olhar; a regra vai na 'explicacao')")
    if t == "escolha":
        ops = _lista_str(d.get("opcoes"), "opcoes", 2)
        if len(set(ops)) != len(ops):
            raise ValueError("escolha: opções repetidas")
        if d.get("correta") not in ops:
            raise ValueError("escolha: 'correta' tem de ser uma das 'opcoes'")
    elif t == "achar_erro":
        segs = _lista_str(d.get("segmentos"), "segmentos", 2)
        if not isinstance(d.get("errado"), int) or not 0 <= d["errado"] < len(segs):
            raise ValueError("achar_erro: 'errado' é o índice do segmento errado")
        if not isinstance(d.get("correcao"), str) or not d["correcao"].strip():
            raise ValueError("achar_erro: falta 'correcao'")
    elif t == "ligar":
        pares = d.get("pares")
        if not isinstance(pares, list) or not 3 <= len(pares) <= 6 or not all(
                isinstance(p, list) and len(p) == 2 and all(isinstance(x, str) and x for x in p) for p in pares):
            raise ValueError("ligar: 'pares' é uma lista de 3 a 6 pares [esquerda, direita]")
        for lado in (0, 1):
            if len({p[lado] for p in pares}) != len(pares):
                raise ValueError("ligar: um lado tem itens repetidos")
    elif t == "ordenar":
        pecas = _lista_str(d.get("pecas"), "pecas", 2)
        for ac in d.get("aceitas") or []:
            if sorted(ac) != sorted(pecas):
                raise ValueError("ordenar: toda 'aceita' é uma permutação de 'pecas'")
        if d.get("distratores") is not None:
            _lista_str(d["distratores"], "distratores")
    elif t == "completar":
        texto, lacunas = d.get("texto"), d.get("lacunas")
        if not isinstance(texto, str) or not isinstance(lacunas, list) or not lacunas:
            raise ValueError("completar: precisa de 'texto' e 'lacunas'")
        marcas = [int(x) for x in re.findall(r"\{(\d+)\}", texto)]
        if sorted(marcas) != list(range(len(lacunas))):
            raise ValueError("completar: o texto deve ter {0}, {1}… uma vez para cada lacuna")
        for i, l in enumerate(lacunas):
            ac = _lista_str(l.get("aceitas"), f"lacunas[{i}].aceitas")
            if l.get("opcoes") is not None and not set(ac) <= set(_lista_str(l["opcoes"], f"lacunas[{i}].opcoes", 2)):
                raise ValueError(f"completar: as aceitas da lacuna {i} têm de estar nas opções")
    elif t == "digitar":
        _lista_str(d.get("aceitas"), "aceitas")
    elif t == "conjugar":
        if not d.get("verbo") or not d.get("forma"):
            raise ValueError("conjugar: precisa de 'verbo' e 'forma'")
        _lista_str(d.get("aceitas"), "aceitas")
    elif t == "ouvir":
        if not isinstance(d.get("texto"), str) or not d["texto"].strip():
            raise ValueError("ouvir: falta 'texto' (a frase falada, que é a resposta)")
        if d.get("fala") is not None and (not isinstance(d["fala"], str) or not d["fala"].strip()):
            raise ValueError("ouvir: 'fala' é o texto que a voz lê")
        if d.get("voz", "F") not in audio.VOZES:
            raise ValueError(f"ouvir: 'voz' é uma de {sorted(audio.VOZES)}")
        if d.get("opcoes") is not None:
            ops = _lista_str(d["opcoes"], "opcoes", 2)
            if len(set(ops)) != len(ops) or d.get("correta") not in ops:
                raise ValueError("ouvir (compreensão): opções sem repetir e 'correta' entre elas")
        elif d.get("aceitas") is not None:
            _lista_str(d["aceitas"], "aceitas")
    elif t == "producao":
        if not isinstance(d.get("minimo", 1), int) or d.get("minimo", 1) < 1:
            raise ValueError("producao: 'minimo' é um inteiro ≥ 1")
    elif t == EXPLICACAO:
        # o slug é conferido contra o caderno no criar_licao, que tem o banco
        md, slug = d.get("md"), d.get("regra")
        if (md is None) == (slug is None):
            raise ValueError("explicacao: 'dados' é {'md': '<markdown>'} ou {'regra': '<slug>'}, um dos dois")
        if md is not None and (not isinstance(md, str) or not md.strip()):
            raise ValueError("explicacao: 'md' é o texto em markdown, não vazio")
        if slug is not None and (not isinstance(slug, str) or not slug.strip()):
            raise ValueError("explicacao: 'regra' é o slug de uma regra do caderno")


# ------------------------------------------------------------------ render

def render(tipo: str, dados: dict, semente: int) -> dict:
    """O que o navegador vê: sem gabarito, embaralhado de forma estável por exercício
    (recarregar a página não troca a ordem das opções)."""
    rnd = random.Random(semente)

    def embaralhar(xs):
        xs = list(xs)
        rnd.shuffle(xs)
        return xs

    if tipo == "escolha":
        return {"opcoes": embaralhar(dados["opcoes"])}
    if tipo == "achar_erro":
        return {"segmentos": dados["segmentos"]}
    if tipo == "ligar":
        return {"esquerda": embaralhar(p[0] for p in dados["pares"]),
                "direita": embaralhar(p[1] for p in dados["pares"])}
    if tipo == "ordenar":
        pecas = list(dados["pecas"]) + list(dados.get("distratores") or [])
        aceitas = [list(a) for a in (dados.get("aceitas") or [dados["pecas"]])]
        mistura = embaralhar(pecas)
        tentativas = 0
        while mistura[:len(dados["pecas"])] in aceitas and tentativas < 20:  # nunca entregar a resposta pronta
            mistura = embaralhar(pecas)
            tentativas += 1
        return {"pecas": mistura}
    if tipo == "completar":
        partes = []
        for i, trecho in enumerate(re.split(r"\{(\d+)\}", dados["texto"])):
            if i % 2 == 0:
                if trecho:
                    partes.append(trecho)
            else:
                lac = dados["lacunas"][int(trecho)]
                item = {"lacuna": int(trecho)}
                if lac.get("opcoes"):
                    item["opcoes"] = embaralhar(lac["opcoes"])
                partes.append(item)
        return {"partes": partes}
    if tipo == "digitar":
        return {"dica": dados.get("dica")} if dados.get("dica") else {}
    if tipo == "conjugar":
        return {k: dados[k] for k in ("verbo", "leitura", "forma") if dados.get(k)}
    if tipo == "ouvir":      # nunca o texto: é a resposta
        r = {"modo": "escolha" if dados.get("opcoes") else "ditado",
             "audio": f"/api/audio/{dados['audio']}.mp3" if dados.get("audio") else None}
        if dados.get("opcoes"):
            r["opcoes"] = embaralhar(dados["opcoes"])
        return r
    if tipo == "producao":
        return {"minimo": dados.get("minimo", 1), "dicas": dados.get("dicas") or []}
    if tipo == EXPLICACAO:      # o {'regra': slug} é resolvido em _render_explicacao, que tem o banco
        return {"md": dados.get("md") or "", "titulo": None, "regra": None}
    raise ValueError(f"tipo desconhecido: {tipo}")


def _render_explicacao(con, dados: dict) -> dict:
    """O markdown de uma regra é lido na hora de mostrar: o tutor pode melhorar a explicação
    no caderno depois de criar a lição, e a lição mostra a versão nova."""
    if not dados.get("regra"):
        return render(EXPLICACAO, dados, 0)
    r = con.execute("SELECT titulo, explicacao_md FROM regra WHERE slug = ?", (dados["regra"],)).fetchone()
    if not r:
        return {"md": f"*(a regra `{dados['regra']}` não está mais no caderno)*", "titulo": None, "regra": dados["regra"]}
    return {"md": r["explicacao_md"] or "*(regra sem explicação)*", "titulo": r["titulo"], "regra": dados["regra"]}


# ------------------------------------------------------------------ correção

def corrigir(tipo: str, dados: dict, resp: dict) -> tuple[str, str, dict]:
    """(veredito, gabarito, detalhe). Determinística: refazer a correção dá o mesmo resultado."""
    if tipo == "escolha":
        ok = normalizar(resp.get("opcao", "")) == normalizar(dados["correta"])
        return ("certo" if ok else "errado"), dados["correta"], {}

    if tipo == "achar_erro":
        segs, i = dados["segmentos"], dados["errado"]
        gab = f"{segs[i]} → {dados['correcao']}"
        return ("certo" if resp.get("segmento") == i else "errado"), gab, {"errado": i, "correcao": dados["correcao"]}

    if tipo == "ligar":
        certa = {a: b for a, b in dados["pares"]}
        escolhidas = {p[0]: p[1] for p in resp.get("pares", []) if isinstance(p, list) and len(p) == 2}
        det = [{"esquerda": a, "escolhida": escolhidas.get(a), "certa": b, "ok": escolhidas.get(a) == b}
               for a, b in dados["pares"]]
        ok = all(x["ok"] for x in det)
        return ("certo" if ok else "errado"), " · ".join(f"{a} — {b}" for a, b in dados["pares"]), {"pares": det}

    if tipo == "ordenar":
        montada = "".join(resp.get("pecas", []))
        aceitas = ["".join(a) for a in (dados.get("aceitas") or [dados["pecas"]])]
        ok = normalizar(montada) in {normalizar(a) for a in aceitas}
        return ("certo" if ok else "errado"), aceitas[0], {"montada": montada}

    if tipo == "completar":
        dadas = list(resp.get("lacunas", []))
        oks = [i < len(dadas) and normalizar(dadas[i]) in {normalizar(a) for a in lac["aceitas"]}
               for i, lac in enumerate(dados["lacunas"])]
        gab = re.sub(r"\{(\d+)\}", lambda m: dados["lacunas"][int(m.group(1))]["aceitas"][0], dados["texto"])
        return ("certo" if all(oks) else "errado"), gab, {"lacunas": oks}

    if tipo == "ouvir" and dados.get("opcoes"):
        ok = normalizar(resp.get("opcao", "")) == normalizar(dados["correta"])
        return ("certo" if ok else "errado"), f"{dados['texto']} → {dados['correta']}", {}

    if tipo in ("digitar", "conjugar", "ouvir"):
        texto = resp.get("texto", "")
        aceitas = dados.get("aceitas") or [dados["texto"]]
        if normalizar(texto) in {normalizar(a) for a in aceitas}:
            return "certo", aceitas[0], {"diff": diff(texto, _mais_parecida(texto, aceitas)), "comparado_com": _mais_parecida(texto, aceitas)}
        alvo = _mais_parecida(texto, aceitas)
        # digitar é frase livre: uma resposta fora da lista pode estar certa, quem decide é o tutor.
        # O ditado também: a frase é fixa, mas o IME deixa mil combinações de kanji e kana.
        # conjugar é conjunto fechado: fora da lista é erro.
        return ("errado" if tipo == "conjugar" else "revisar"), aceitas[0], {"diff": diff(texto, alvo), "comparado_com": alvo}

    if tipo == "producao":
        return "revisar", "", {}

    if tipo == EXPLICACAO:
        raise ValueError("explicação não tem resposta: o botão Entendi só avança")

    raise ValueError(f"tipo desconhecido: {tipo}")


def _escrito(tipo: str, resp: dict) -> str:
    """A resposta dele como texto, para a tabela `erro`."""
    if tipo == "escolha":
        return resp.get("opcao", "")
    if tipo in ("digitar", "conjugar"):
        return resp.get("texto", "")
    if tipo == "ouvir":
        return resp.get("opcao") or resp.get("texto", "")
    if tipo == "ordenar":
        return "".join(resp.get("pecas", []))
    if tipo == "completar":
        return " / ".join(resp.get("lacunas", []))
    if tipo == "ligar":
        return " · ".join(f"{a} — {b}" for a, b in resp.get("pares", []))
    if tipo == "achar_erro":
        return f"segmento {resp.get('segmento')}"
    if tipo == "producao":
        return "\n".join(resp.get("frases", []))
    return json.dumps(resp, ensure_ascii=False)


# ------------------------------------------------------------------ lições (banco)

def _regra_id(con, slug: str, precisa_texto: bool = False) -> int:
    r = con.execute("SELECT id, explicacao_md FROM regra WHERE slug = ?", (slug,)).fetchone()
    if not r:
        raise ValueError(f"a regra '{slug}' não está no caderno (crie com salvar_regra ou importe; "
                         "regras(vencidas=False) lista as que existem)")
    if precisa_texto and not (r["explicacao_md"] or "").strip():
        raise ValueError(f"a regra '{slug}' não tem explicacao_md (grave com salvar_regra ou use {{'md': ...}})")
    return r["id"]


def criar_licao(con: sqlite3.Connection, titulo: str, exercicios: list[ExercicioIn], data: str | None = None) -> int:
    """Tudo ou nada: um exercício inválido recusa a lição inteira, com o índice dele na mensagem."""
    ids_regra: list[int | None] = []
    for i, ex in enumerate(exercicios):
        try:
            validar(ex)
            if ex.tipo == EXPLICACAO and ex.dados.get("regra"):
                _regra_id(con, ex.dados["regra"], precisa_texto=True)
            ids_regra.append(_regra_id(con, ex.regra) if ex.regra else None)
        except ValueError as e:
            raise ValueError(f"exercício {i + 1} ({ex.tipo}): {e}") from None
    todos_dados = []
    for i, ex in enumerate(exercicios):
        d = dict(ex.dados)
        if ex.tipo == "ouvir":
            try:
                d["audio"] = audio.garantir(d.get("fala") or d["texto"], d.get("voz", "F"))
            except Exception as e:      # sem rede: o tutor troca o tipo, a lição não nasce pela metade
                raise ValueError(f"exercício {i + 1} (ouvir): não consegui gravar o áudio ({type(e).__name__}: {e}). "
                                 "Sem rede? Troque este exercício por outro tipo.") from None
        todos_dados.append(d)
    data = data or dominio.dia_de_estudo().isoformat()
    cur = con.execute("INSERT INTO licao (data, titulo) VALUES (?, ?)", (data, titulo))
    lid = cur.lastrowid
    con.executemany("""INSERT INTO exercicio (licao_id, ordem, bloco, tipo, categoria, enunciado, dados, explicacao,
                                             regra_id, dica_erro)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [(lid, i + 1, ex.bloco, ex.tipo, ex.categoria, ex.enunciado or "",
                      json.dumps(d, ensure_ascii=False), ex.explicacao, rid,
                      ex.dica_erro.strip() if ex.dica_erro else None)
                     for i, (ex, d, rid) in enumerate(zip(exercicios, todos_dados, ids_regra))])
    con.commit()
    return lid


def _primeira_resposta(con, exercicio_id: int):
    """A resposta que conta. Sempre a de menor id, e nunca uma 2ª tentativa (§9.6)."""
    return con.execute("SELECT * FROM resposta WHERE exercicio_id = ? AND apos_dica = 0 ORDER BY id LIMIT 1",
                       (exercicio_id,)).fetchone()


def _segunda_tentativa(con, exercicio_id: int):
    """A 2ª tentativa depois da dica, ou a desistência (§9.6). Nunca mais de uma: o servidor só grava
    `apos_dica = 1` enquanto a dica está pendente."""
    return con.execute("SELECT * FROM resposta WHERE exercicio_id = ? AND apos_dica = 1 ORDER BY id LIMIT 1",
                       (exercicio_id,)).fetchone()


def _com_dica(ex, r1) -> bool:
    """A 1ª resposta abriu a 2ª tentativa? Só se o exercício tem dica e a correção AUTOMÁTICA dela
    deu errado. Recalcula em vez de ler o veredito gravado: um 'revisar' fechado como errado pelo
    tutor não é caso de dica (§9.6), e a correção é determinística."""
    return bool(ex["dica_erro"]) and corrigir(ex["tipo"], json.loads(ex["dados"]), json.loads(r1["resposta"]))[0] == "errado"


def _aguardando_dica(con, ex, r1) -> bool:
    return r1 is not None and _com_dica(ex, r1) and _segunda_tentativa(con, ex["id"]) is None


def _resultado(ex, r1, r2=None) -> dict | None:
    if not r1:
        return None
    dados, resp = json.loads(ex["dados"]), json.loads(r1["resposta"])
    _v, gabarito, _d = corrigir(ex["tipo"], dados, resp)
    res = {"veredito": r1["veredito"], "resposta": resp, "gabarito": gabarito, "explicacao": ex["explicacao"],
           "detalhe": json.loads(r1["detalhe"]) if r1["detalhe"] else {}, "correcao": r1["correcao"],
           "dica": None, "segunda": None, "autocorrigiu": None}
    if not _com_dica(ex, r1):
        return res
    res["dica"] = ex["dica_erro"]
    if r2 is None:      # dica pendente: o gabarito não sai do servidor antes da 2ª tentativa
        return {**res, "gabarito": "", "explicacao": None, "detalhe": {}}
    resp2 = json.loads(r2["resposta"])
    if resp2.get("desistiu"):
        res["segunda"] = {"desistiu": True}
    else:
        res["segunda"] = {"resposta": resp2, "veredito": r2["veredito"],
                          "detalhe": json.loads(r2["detalhe"]) if r2["detalhe"] else {}}
    res["autocorrigiu"] = r2["veredito"] == "certo" and not resp2.get("desistiu")
    return res


def licao_renderizada(con, licao_id: int) -> dict | None:
    l = con.execute("SELECT * FROM licao WHERE id = ?", (licao_id,)).fetchone()
    if not l:
        return None
    exs = []
    for ex in con.execute("SELECT * FROM exercicio WHERE licao_id = ? ORDER BY ordem", (licao_id,)).fetchall():
        dados = json.loads(ex["dados"])
        rend = _render_explicacao(con, dados) if ex["tipo"] == EXPLICACAO else render(ex["tipo"], dados, semente=ex["id"])
        exs.append({"id": ex["id"], "ordem": ex["ordem"], "bloco": ex["bloco"], "tipo": ex["tipo"],
                    "categoria": ex["categoria"], "enunciado": ex["enunciado"], "render": rend,
                    "resultado": _resultado(ex, _primeira_resposta(con, ex["id"]), _segunda_tentativa(con, ex["id"]))})
    return {"id": l["id"], "data": l["data"], "titulo": l["titulo"], "status": l["status"], "exercicios": exs}


def licao_atual_id(con) -> int | None:
    r = con.execute("SELECT id FROM licao WHERE status = 'aberta' ORDER BY id DESC LIMIT 1").fetchone() \
        or con.execute("SELECT id FROM licao ORDER BY id DESC LIMIT 1").fetchone()
    return r["id"] if r else None


def _exercicio(con, exercicio_id: int):
    ex = con.execute("""SELECT e.*, l.data AS data_licao FROM exercicio e JOIN licao l ON l.id = e.licao_id
                        WHERE e.id = ?""", (exercicio_id,)).fetchone()
    if not ex:
        raise KeyError(exercicio_id)
    return ex


def responder(con, exercicio_id: int, resp: dict, tempo_ms: int | None = None) -> dict:
    """Grava uma resposta. Quem decide o que ela é, é o servidor: a 1ª (conta no placar), a 2ª
    tentativa depois da dica (§9.6, `apos_dica = 1`) ou o "Praticar de novo" (não conta)."""
    ex = _exercicio(con, exercicio_id)
    dados = json.loads(ex["dados"])
    veredito, gabarito, detalhe = corrigir(ex["tipo"], dados, resp)     # ValueError no explicacao
    r1 = _primeira_resposta(con, exercicio_id)
    segunda = _aguardando_dica(con, ex, r1)
    con.execute("""INSERT INTO resposta (exercicio_id, resposta, veredito, detalhe, tempo_ms, apos_dica)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (exercicio_id, json.dumps(resp, ensure_ascii=False), veredito,
                 json.dumps(detalhe, ensure_ascii=False), tempo_ms, int(segunda)))
    if r1 is None:
        if veredito == "errado":
            _gravar_erro(con, ex, _escrito(ex["tipo"], resp), gabarito)
        if ex["regra_id"] and veredito in ("certo", "errado"):    # o 'revisar' agenda quando o tutor fecha
            regras.agendar(con, ex["regra_id"], veredito, dominio.dia_de_estudo())
    elif segunda and veredito == "certo":
        _marcar_deslize(con, ex, r1)
    _fechar_se_completa(con, ex["licao_id"])
    con.commit()
    if r1 is None and veredito == "errado" and ex["dica_erro"]:
        # A dica no lugar da resposta certa (23/10/2026, §9.6): a dica que faz o aluno se corrigir
        # ensina mais que a resposta pronta. Gabarito, explicação e detalhe ficam para depois.
        return {"veredito": "errado", "gabarito": "", "explicacao": None, "detalhe": {}, "contou": True,
                "dica": ex["dica_erro"]}
    saida = {"veredito": veredito, "gabarito": gabarito, "explicacao": ex["explicacao"], "detalhe": detalhe,
             "contou": r1 is None}
    if segunda:
        saida["autocorrigiu"] = veredito == "certo"
    return saida


def desistir(con, exercicio_id: int) -> dict:
    """"Ver a resposta" com a dica pendente (§9.6): é lacuna. A agenda da regra já foi tratada como
    lacuna na 1ª resposta; aqui só fica registrado que a 2ª tentativa não veio."""
    ex = _exercicio(con, exercicio_id)
    r1 = _primeira_resposta(con, exercicio_id)
    if not _aguardando_dica(con, ex, r1):
        raise ValueError("este exercício não tem dica esperando a 2ª tentativa")
    con.execute("INSERT INTO resposta (exercicio_id, resposta, veredito, apos_dica) VALUES (?, ?, 'errado', 1)",
                (exercicio_id, json.dumps({"desistiu": True})))
    con.commit()
    _v, gabarito, detalhe = corrigir(ex["tipo"], json.loads(ex["dados"]), json.loads(r1["resposta"]))
    return {"veredito": "errado", "gabarito": gabarito, "explicacao": ex["explicacao"], "detalhe": detalhe,
            "contou": False, "autocorrigiu": False}


def _marcar_deslize(con, ex, r1) -> None:
    """A 2ª tentativa saiu certa: o erro da 1ª vira deslize na tabela `erro` e na agenda da regra."""
    con.execute("UPDATE erro SET deslize = 1 WHERE id = (SELECT MAX(id) FROM erro WHERE exercicio_id = ?)",
                (ex["id"],))
    if ex["regra_id"]:
        # o dia da FALHA, não o de agora: a 2ª tentativa pode vir depois das 04:00 (§13.2)
        dia_falha = dominio.dia_de_estudo(datetime.fromisoformat(r1["criado_em"]))
        regras.deslize(con, ex["regra_id"], dia_falha)


def _gravar_erro(con, ex, escrito: str, correto: str) -> None:
    con.execute("""INSERT INTO erro (data, bloco, categoria, escrito, correto, porque, exercicio_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (ex["data_licao"], _BLOCO_ERRO[ex["bloco"]], ex["categoria"] or "outro", escrito, correto,
                 ex["explicacao"], ex["id"]))


def _fechar_se_completa(con, licao_id: int) -> None:
    # o explicacao não tem resposta: se contasse, a lição nunca concluiria. E a dica pendente (§9.6)
    # não segura a lição: a 1ª resposta já está dada, e uma dica abandonada não pode deixar a lição
    # aberta para sempre (a "lição atual" do painel é a aberta mais recente).
    (faltam,) = con.execute("""SELECT COUNT(*) FROM exercicio e WHERE e.licao_id = ? AND e.tipo != 'explicacao'
                               AND NOT EXISTS (SELECT 1 FROM resposta r WHERE r.exercicio_id = e.id)""",
                            (licao_id,)).fetchone()
    if not faltam:
        con.execute("UPDATE licao SET status = 'concluida', concluida_em = datetime('now', 'localtime') "
                    "WHERE id = ? AND status = 'aberta'", (licao_id,))


def corrigir_revisao(con, exercicio_id: int, veredito: str, correcao: str) -> bool:
    """O tutor fecha um 'revisar' (digitar fora da lista, produção)."""
    if veredito not in ("certo", "errado"):
        raise ValueError("veredito deve ser 'certo' ou 'errado'")
    r = _primeira_resposta(con, exercicio_id)
    if not r:
        return False
    ex = _exercicio(con, exercicio_id)
    con.execute("UPDATE resposta SET veredito = ?, correcao = ? WHERE id = ?", (veredito, correcao, r["id"]))
    if veredito == "errado" and r["veredito"] != "errado":
        _gravar_erro(con, ex, _escrito(ex["tipo"], json.loads(r["resposta"])), correcao[:300])
    # Só o primeiro fechamento move a agenda: um certo/errado automático já agendou na resposta,
    # e o tutor reescrever a correção não pode contar a mesma revisão duas vezes.
    if r["veredito"] == "revisar" and ex["regra_id"]:
        regras.agendar(con, ex["regra_id"], veredito, dominio.dia_de_estudo())
    con.commit()
    return True


def resumo_licoes(con, ultimas: int = 20) -> list[dict]:
    saida = []
    for l in con.execute("SELECT * FROM licao ORDER BY id DESC LIMIT ?", (ultimas,)):
        cont = {"certo": 0, "errado": 0, "revisar": 0}
        total = pend = 0
        for ex in con.execute("SELECT id FROM exercicio WHERE licao_id = ? AND tipo != 'explicacao'", (l["id"],)):
            total += 1
            r = _primeira_resposta(con, ex["id"])
            if r:
                cont[r["veredito"]] += 1
            else:
                pend += 1
        saida.append({"id": l["id"], "data": l["data"], "titulo": l["titulo"], "status": l["status"],
                      "total": total, "certos": cont["certo"], "errados": cont["errado"],
                      "revisar": cont["revisar"], "pendentes": pend})
    return saida


# ------------------------------------------------------------------ sorteio dos tipos

def planejar_tipos(con, n: int = len(TIPOS), semente: int | None = None) -> dict:
    """'Sempre variando, mas utilizando todos' (DESIGN §9.4)."""
    rnd = random.Random(semente)
    ultimas = [r["id"] for r in con.execute("SELECT id FROM licao ORDER BY id DESC LIMIT 2")]
    recentes = {r["tipo"] for r in con.execute(
        f"SELECT DISTINCT tipo FROM exercicio WHERE licao_id IN ({','.join('?' * len(ultimas)) or 'NULL'})", ultimas)}
    desde = (dominio.dia_de_estudo() - timedelta(days=30)).isoformat()
    taxa = {}
    for tipo, erros, total in con.execute("""
            SELECT e.tipo, SUM(r.veredito = 'errado'), COUNT(*) FROM exercicio e
            JOIN licao l ON l.id = e.licao_id
            JOIN resposta r ON r.id = (SELECT MIN(id) FROM resposta WHERE exercicio_id = e.id)
            WHERE l.data >= ? AND r.veredito IN ('certo', 'errado') GROUP BY e.tipo""", (desde,)):
        taxa[tipo] = (erros or 0) / total if total else 0.0

    pesos = {t: round(1 + (2 if t not in recentes else 0) + 2 * taxa.get(t, 0.0), 2) for t in TIPOS}
    outros = [t for t in TIPOS if t != "producao"]
    # Teto de 2 por tipo enquanto couber. Desde 21/10/2026 a lição tem 20 exercícios (pedido dele:
    # "mais questões sobre o conteúdo novo de cada dia"), e com 8 tipos o teto de 2 parava em 17:
    # acima disso ele sobe só o necessário para fechar a conta (3 com 20; e com 25, desde 23/10).
    teto = max(2, -(-(n - 1) // len(outros)))
    escolha: list[str] = []
    if n - 1 >= len(outros):            # cabe todo mundo: cada tipo uma vez, o resto sorteado
        escolha = list(outros)
    while len(escolha) < n - 1:
        livres = [t for t in outros if escolha.count(t) < teto]
        if not livres:
            break
        escolha.append(rnd.choices(livres, weights=[pesos[t] for t in livres])[0])
    rnd.shuffle(escolha)
    escolha.append("producao")          # produção ativa todo dia, sempre no fim
    return {"tipos": escolha, "pesos": pesos,
            "motivo": "peso = 1 + 2 se ausente nas 2 últimas lições + 2 × taxa de erro do tipo em 30 dias"}
