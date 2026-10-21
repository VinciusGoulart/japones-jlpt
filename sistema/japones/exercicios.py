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
from datetime import timedelta
from typing import Literal

from pydantic import BaseModel, Field

from japones import audio, dominio

TIPOS = ("escolha", "achar_erro", "ligar", "ordenar", "completar", "digitar", "conjugar", "ouvir", "producao")
BLOCOS = ("aquecimento", "verificacao", "producao", "revisao")
# bloco do exercício -> bloco da tabela `erro`
_BLOCO_ERRO = {"aquecimento": "abertura", "verificacao": "verificacao", "producao": "producao", "revisao": "outro"}


class ExercicioIn(BaseModel):
    tipo: Literal["escolha", "achar_erro", "ligar", "ordenar", "completar", "digitar", "conjugar", "ouvir",
                  "producao"]
    bloco: Literal["aquecimento", "verificacao", "producao", "revisao"] = "verificacao"
    enunciado: str = Field(description="a instrução, em português")
    dados: dict = Field(description="por tipo, DESIGN §9.2 — com o gabarito")
    explicacao: str | None = Field(default=None, description="a regra, mostrada depois da resposta")
    categoria: str | None = Field(default=None, description="categoria de erro (DESIGN §4.2)")


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
    raise ValueError(f"tipo desconhecido: {tipo}")


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

def criar_licao(con: sqlite3.Connection, titulo: str, exercicios: list[ExercicioIn], data: str | None = None) -> int:
    """Tudo ou nada: um exercício inválido recusa a lição inteira, com o índice dele na mensagem."""
    for i, ex in enumerate(exercicios):
        try:
            validar(ex)
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
    con.executemany("""INSERT INTO exercicio (licao_id, ordem, bloco, tipo, categoria, enunciado, dados, explicacao)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    [(lid, i + 1, ex.bloco, ex.tipo, ex.categoria, ex.enunciado,
                      json.dumps(d, ensure_ascii=False), ex.explicacao)
                     for i, (ex, d) in enumerate(zip(exercicios, todos_dados))])
    con.commit()
    return lid


def _primeira_resposta(con, exercicio_id: int):
    return con.execute("SELECT * FROM resposta WHERE exercicio_id = ? ORDER BY id LIMIT 1", (exercicio_id,)).fetchone()


def _resultado(ex, r) -> dict | None:
    if not r:
        return None
    dados, resp = json.loads(ex["dados"]), json.loads(r["resposta"])
    _v, gabarito, _d = corrigir(ex["tipo"], dados, resp)
    return {"veredito": r["veredito"], "resposta": resp, "gabarito": gabarito, "explicacao": ex["explicacao"],
            "detalhe": json.loads(r["detalhe"]) if r["detalhe"] else {}, "correcao": r["correcao"]}


def licao_renderizada(con, licao_id: int) -> dict | None:
    l = con.execute("SELECT * FROM licao WHERE id = ?", (licao_id,)).fetchone()
    if not l:
        return None
    exs = []
    for ex in con.execute("SELECT * FROM exercicio WHERE licao_id = ? ORDER BY ordem", (licao_id,)):
        exs.append({"id": ex["id"], "ordem": ex["ordem"], "bloco": ex["bloco"], "tipo": ex["tipo"],
                    "categoria": ex["categoria"], "enunciado": ex["enunciado"],
                    "render": render(ex["tipo"], json.loads(ex["dados"]), semente=ex["id"]),
                    "resultado": _resultado(ex, _primeira_resposta(con, ex["id"]))})
    return {"id": l["id"], "data": l["data"], "titulo": l["titulo"], "status": l["status"], "exercicios": exs}


def licao_atual_id(con) -> int | None:
    r = con.execute("SELECT id FROM licao WHERE status = 'aberta' ORDER BY id DESC LIMIT 1").fetchone() \
        or con.execute("SELECT id FROM licao ORDER BY id DESC LIMIT 1").fetchone()
    return r["id"] if r else None


def responder(con, exercicio_id: int, resp: dict, tempo_ms: int | None = None) -> dict:
    ex = con.execute("""SELECT e.*, l.data AS data_licao FROM exercicio e JOIN licao l ON l.id = e.licao_id
                        WHERE e.id = ?""", (exercicio_id,)).fetchone()
    if not ex:
        raise KeyError(exercicio_id)
    dados = json.loads(ex["dados"])
    veredito, gabarito, detalhe = corrigir(ex["tipo"], dados, resp)
    primeira = _primeira_resposta(con, exercicio_id) is None
    con.execute("INSERT INTO resposta (exercicio_id, resposta, veredito, detalhe, tempo_ms) VALUES (?, ?, ?, ?, ?)",
                (exercicio_id, json.dumps(resp, ensure_ascii=False), veredito,
                 json.dumps(detalhe, ensure_ascii=False), tempo_ms))
    if primeira and veredito == "errado":
        _gravar_erro(con, ex, _escrito(ex["tipo"], resp), gabarito)
    _fechar_se_completa(con, ex["licao_id"])
    con.commit()
    return {"veredito": veredito, "gabarito": gabarito, "explicacao": ex["explicacao"], "detalhe": detalhe,
            "contou": primeira}


def _gravar_erro(con, ex, escrito: str, correto: str) -> None:
    con.execute("INSERT INTO erro (data, bloco, categoria, escrito, correto, porque) VALUES (?, ?, ?, ?, ?, ?)",
                (ex["data_licao"], _BLOCO_ERRO[ex["bloco"]], ex["categoria"] or "outro", escrito, correto,
                 ex["explicacao"]))


def _fechar_se_completa(con, licao_id: int) -> None:
    (faltam,) = con.execute("""SELECT COUNT(*) FROM exercicio e WHERE e.licao_id = ?
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
    con.execute("UPDATE resposta SET veredito = ?, correcao = ? WHERE id = ?", (veredito, correcao, r["id"]))
    if veredito == "errado" and r["veredito"] != "errado":
        ex = con.execute("""SELECT e.*, l.data AS data_licao FROM exercicio e JOIN licao l ON l.id = e.licao_id
                            WHERE e.id = ?""", (exercicio_id,)).fetchone()
        _gravar_erro(con, ex, _escrito(ex["tipo"], json.loads(r["resposta"])), correcao[:300])
    con.commit()
    return True


def resumo_licoes(con, ultimas: int = 20) -> list[dict]:
    saida = []
    for l in con.execute("SELECT * FROM licao ORDER BY id DESC LIMIT ?", (ultimas,)):
        cont = {"certo": 0, "errado": 0, "revisar": 0}
        total = pend = 0
        for ex in con.execute("SELECT id FROM exercicio WHERE licao_id = ?", (l["id"],)):
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
    # acima disso ele sobe só o necessário para fechar a conta (3 com 20).
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
