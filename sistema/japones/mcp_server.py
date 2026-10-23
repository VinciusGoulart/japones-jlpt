"""Servidor MCP do tutor: o Claude Code consulta o estudo em vez de ler arquivos.

Contrato em sistema/DESIGN.md §6. Regra que vale para todas as ferramentas:
nenhuma fonte externa derruba a resposta. Se o Trello, o Anki ou o Kotoba
falharem, o campo vem como {"erro": "..."} e o resto segue — nenhuma
ferramenta pode ser pré-requisito da hora de estudo.

As respostas são enxutas de propósito: cada token aqui é reenviado a cada
mensagem da aula, e foi o tamanho do contexto que estourou o limite em 27/09.
"""
import contextlib
import re
import shutil
import sqlite3
import sys
from datetime import date, datetime, timedelta

from pydantic import BaseModel, Field
from mcp.server import MCPServer

from japones import config, db, dominio
from japones import regras as caderno
from japones.fontes import curriculo, diario

mcp = MCPServer(
    "japones",
    instructions=(
        "Sistema de estudo de japonês do Vinicius. No Passo 0 da /estudo, chame hoje() — ele substitui "
        "date, trello.py status, anki_status.py, a leitura do estado.json e do curriculo.md. "
        "Depois de ensinar, monte os exercícios: planejar_tipos() → criar_licao() → ele faz no painel → "
        "resultado_licao() → corrigir_exercicio() nos 'revisar'. "
        "Regras de gramática vencidas (hoje().regras_vencidas, regras()) entram na lição com o campo `regra`; "
        "regra ensinada hoje vai para o caderno com salvar_regra(). "
        "No Passo 4, registre com registrar_aula, registrar_trajeto e registrar_erros, e feche com backup(). "
        "Antes de ensinar uma palavra ou leitura de que não tenha certeza, confira com dicionario()."
    ),
)


def _seguro(f, *args, **kw):
    # O stdout é o canal do protocolo MCP: um print() perdido de uma ferramenta
    # reaproveitada de tools/ corromperia a resposta. Tudo que elas imprimirem vai para o stderr.
    try:
        with contextlib.redirect_stdout(sys.stderr):
            return f(*args, **kw)
    except Exception as e:  # a fonte caiu: a aula não cai junto
        return {"erro": f"{type(e).__name__}: {e}"}


def _con():
    return db.conectar()


def _agora() -> datetime:
    """O relógio real, num ponto só: os testes trocam esta função (o aviso da madrugada do hoje()
    depende da hora de verdade, não do dia de estudo)."""
    return datetime.now()


# 23/10/2026, recomendação do relatório de pesquisa aprovada por ele: o sono curto prejudica a
# codificação e a memória de trabalho, e conteúdo novo depois da 1h de um dia de trabalho rende pouco.
AVISO_MADRUGADA = ("Depois da 1h em véspera de trabalho: aula só de revisão (regras vencidas + produção curta, "
                   "até 30 min); o conteúdo novo passa para a próxima sessão.")


def _madrugada_de_trabalho(agora: datetime) -> bool:
    """01:00–03:59 do relógio real num dia de CALENDÁRIO de segunda a sexta — o dia em que ele trabalha.
    A 01:30 de sábado (sessão da sexta à noite) não avisa; a 01:30 de segunda avisa."""
    return 1 <= agora.hour < 4 and agora.weekday() < 5


def _amanha_da_entrada(texto: str) -> str | None:
    m = re.search(r"^\*\*Amanhã:\*\*\s*(.+)$", texto, re.M)
    return m.group(1).strip() if m else None


def _datas_com_aula(con) -> set[date]:
    return {date.fromisoformat(r[0]) for r in
            con.execute("SELECT DISTINCT data FROM aula WHERE tipo IN ('completa', 'parcial')")}


def _resumo_anki() -> dict:
    from japones.fontes import anki
    a = anki.status()
    hoje_, ontem = a["ultimos_7_dias"][-1], a["ultimos_7_dias"][-2]
    return {
        "leitura": f"{a['fonte']['fonte']}, há {a['fonte']['idade_dias']} dia(s)",
        "hoje": {"cartoes": hoje_["cartoes"], "minutos": hoje_["minutos"]},
        "ontem": {"cartoes": ontem["cartoes"], "minutos": ontem["minutos"]},
        "fila_atrasados": a["fila_atrasados"], "alerta_fila": a["alerta_fila"],
        "retencao_30d": a["retencao_30d"], "alerta_retencao": a["alerta_retencao"],
        "em_loop": [f"{x['frente']} ({x['again_7d']}x)" for x in a["em_loop"][:10]],
        "bandeira": [x["frente"] for x in a["bandeira"]],
    }


def _resumo_trello(hoje: date) -> dict:
    from japones.fontes import trello
    b = trello.board(hoje)
    limite = (hoje + timedelta(days=7)).isoformat()
    pend = [{"nome": p["nome"], "vence": p["vence"], "vencido": p["vencido"], "url": p["url"]}
            for p in trello.pendencias(b) if p["vence"] and p["vence"] <= limite]
    semana = [{"card": c["nome"], "checklists": [{"nome": cl["nome"], "feitos": f"{cl['feitos']}/{cl['total']}",
                                                  "faltam": cl["faltam"]} for cl in c["checklists"]]}
              for c in trello.semana_atual(b)]
    avisos = [{"nome": c["nome"], "url": c["url"]} for c in b["listas"].get("Avisos do JLPT", [])]
    return {"pendencias_7_dias": pend, "semana_atual": semana, "avisos_jlpt": avisos}


# ------------------------------------------------------------------ leitura

@mcp.tool()
def hoje() -> dict:
    """O Passo 0 inteiro: dia de estudo (regra das 04:00), dia do plano, streak, última aula e o que ela
    deixou para hoje, plano do dia, lembrete de abertura, padrões abertos, regras de gramática vencidas
    (total e até 5 slugs), Trello (pendências da semana, checklists, avisos do JLPT) e Anki (fila, retenção,
    cartões em loop, bandeira). Entre 01:00 e 03:59 de um dia útil, `avisos` traz a regra da madrugada:
    aula só de revisão."""
    agora = _agora()
    d = dominio.dia_de_estudo(agora)
    con = _con()
    datas = _datas_com_aula(con)
    atual, recorde = dominio.streak(datas, d)
    ult = con.execute("""SELECT data, dia_plano, tipo, titulo, texto_md FROM aula
                         WHERE tipo IN ('completa', 'parcial') ORDER BY data DESC, id DESC LIMIT 1""").fetchone()
    (max_dia,) = con.execute("SELECT MAX(dia_plano) FROM aula WHERE tipo IN ('completa', 'parcial')").fetchone()
    nota = con.execute("SELECT valor, atualizado_em FROM nota WHERE chave = 'lembrete_abertura'").fetchone()
    padroes = db.linhas(con.execute("SELECT id, categoria, descricao, aberto_em FROM padrao "
                                    "WHERE status = 'aberto' ORDER BY aberto_em DESC"))
    ja_registrada = con.execute("SELECT tipo FROM aula WHERE data = ? AND origem IN ('mcp', 'migracao')",
                                (d.isoformat(),)).fetchone()
    regras_vencidas = caderno.resumo_vencidas(con, d)
    con.close()

    dias_sem = (d - date.fromisoformat(ult["data"])).days if ult else None
    plano = curriculo.do_dia(d)
    avisos = []
    if _madrugada_de_trabalho(agora):       # o relógio real; o resto do hoje() segue o dia de estudo
        avisos.append(AVISO_MADRUGADA)
    if dias_sem is not None and dias_sem >= 3:
        avisos.append(f"RETOMADA: {dias_sem} dias desde a última aula — sessão só de revisão, zerar streak sem drama.")
    if not any(x.year == d.year and x.month == d.month and x < d for x in datas):
        avisos.append("PRIMEIRA SESSÃO DO MÊS: criar o card 'Ação do mês' do Projeto Japão e cuidar do diagnóstico mensal.")
    if d.weekday() == 6:
        avisos.append("DOMINGO: planejar a semana seguinte em curriculo.md e criar os cards no Trello.")
    if ja_registrada:
        avisos.append(f"Já existe aula registrada hoje ({ja_registrada['tipo']}).")

    return {
        "agora": agora.strftime("%Y-%m-%d %H:%M (%a)"),
        "dia_de_estudo": d.isoformat(),
        "dia_do_plano": (max_dia or 0) + 1,
        "streak": {"atual_ate_ontem": atual, "recorde": recorde},
        "ultima_aula": ({"data": ult["data"], "dia": ult["dia_plano"], "tipo": ult["tipo"], "titulo": ult["titulo"],
                         "deixou_para_hoje": _amanha_da_entrada(ult["texto_md"]), "dias_atras": dias_sem}
                        if ult else None),
        "plano_de_hoje": plano["conteudo"] if plano else None,
        "proximos": [f"{p['data']} ({p['dia_semana']}): {p['conteudo']}" for p in curriculo.proximos(d + timedelta(days=1), 3)],
        "lembrete_abertura": ({"texto": nota["valor"], "de": nota["atualizado_em"]} if nota else None),
        "padroes_abertos": padroes,
        "regras_vencidas": regras_vencidas,
        "avisos": avisos,
        "trello": _seguro(_resumo_trello, d),
        "anki": _seguro(_resumo_anki),
    }


@mcp.tool()
def aulas(ultimas: int = 7, busca: str | None = None, desde: str | None = None) -> list[dict]:
    """Aulas resumidas (sem o texto), da mais nova para a mais antiga. `busca` procura no texto do diário;
    `desde` é AAAA-MM-DD."""
    sql = ["SELECT data, dia_plano, tipo, titulo, inicio, minutos, verif_ok, verif_total, prod_ok, prod_total "
           "FROM aula WHERE 1 = 1"]
    params = []
    if busca:
        sql.append("AND texto_md LIKE ?")
        params.append(f"%{busca}%")
    if desde:
        sql.append("AND data >= ?")
        params.append(desde)
    sql.append("ORDER BY data DESC, id DESC LIMIT ?")
    params.append(ultimas)
    con = _con()
    r = db.linhas(con.execute(" ".join(sql), params))
    con.close()
    return r


@mcp.tool()
def aula(data: str) -> list[dict]:
    """A(s) entrada(s) completa(s) do diário de um dia de estudo (AAAA-MM-DD)."""
    con = _con()
    r = db.linhas(con.execute("SELECT * FROM aula WHERE data = ? ORDER BY id", (data,)))
    con.close()
    return r


@mcp.tool()
def erros(categoria: str | None = None, dias: int = 30) -> dict:
    """Erros categorizados dos últimos `dias` (filtro opcional por categoria ou prefixo, ex. 'particula')
    e a contagem por categoria. `deslize` = corrigido com a dica na 2ª tentativa (sabe a regra, escorregou);
    `deslizes_por_categoria` conta só esses (o resto do `por_categoria` são lacunas e erros de fora do painel)."""
    desde = (dominio.dia_de_estudo() - timedelta(days=dias)).isoformat()
    con = _con()
    # prefixo literal: um '_' ou '%' no nome não pode virar curinga do LIKE
    prefixo = (categoria or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    filtro, params = ("AND categoria LIKE ? ESCAPE '\\'", [desde, f"{prefixo}%"]) if categoria else ("", [desde])
    lista = db.linhas(con.execute(f"SELECT data, bloco, categoria, escrito, correto, porque, deslize FROM erro "
                                  f"WHERE data >= ? {filtro} ORDER BY data DESC, id DESC LIMIT 100", params))
    for e in lista:
        e["deslize"] = bool(e["deslize"])
    contagem = dict(con.execute("SELECT categoria, COUNT(*) FROM erro WHERE data >= ? GROUP BY categoria "
                                "ORDER BY COUNT(*) DESC", (desde,)).fetchall())
    deslizes = dict(con.execute("SELECT categoria, COUNT(*) FROM erro WHERE data >= ? AND deslize = 1 "
                                "GROUP BY categoria ORDER BY COUNT(*) DESC", (desde,)).fetchall())
    con.close()
    return {"desde": desde, "por_categoria": contagem, "deslizes_por_categoria": deslizes, "erros": lista}


@mcp.tool()
def padroes(status: str = "aberto") -> list[dict]:
    """Padrões em vigília ('aberto' ou 'resolvido')."""
    con = _con()
    r = db.linhas(con.execute("SELECT * FROM padrao WHERE status = ? ORDER BY aberto_em DESC", (status,)))
    con.close()
    return r


@mcp.tool()
def registro_antigo(busca: str, limite: int = 10) -> list[dict]:
    """Busca no log herdado de pontos_fracos (antes do sistema). Útil para 'isso já aconteceu antes?'."""
    con = _con()
    r = db.linhas(con.execute("SELECT data, texto FROM registro WHERE texto LIKE ? ORDER BY data DESC LIMIT ?",
                              (f"%{busca}%", limite)))
    con.close()
    return r


@mcp.tool()
def anki() -> dict:
    """O status completo do Anki (baralhos, fila, 7 dias, retenção, botões, cartões que travam, em loop, bandeira)."""
    from japones.fontes import anki as fonte
    return _seguro(fonte.status)


@mcp.tool()
def trello() -> dict:
    """O board inteiro do Trello, lista por lista, com checklists e links."""
    from japones.fontes import trello as fonte
    return _seguro(fonte.board, dominio.dia_de_estudo())


@mcp.tool()
def dicionario(termo: str, limite: int = 5) -> dict:
    """Busca no dicionário do Kotoba (japonês, kana ou português): leitura, glosas, nível JLPT, classe.
    Use para conferir leitura e sentido antes de ensinar — a regra é nunca inventar japonês."""
    from japones.fontes import kotoba
    # Enxuto: 持つ tem 19 glosas em português e 18 em inglês; para conferir, as primeiras bastam.
    manter = ("palavra", "grafia_kanji", "leitura", "jlpt", "comum", "classe", "acento", "url")

    def compacto():
        saida = []
        for r in kotoba.buscar(termo, limite):
            c = {k: r[k] for k in manter if r.get(k) not in (None, [], "")}
            c["glosas_pt"] = r.get("glosas_pt", [])[:6]
            c["glosas_en"] = r.get("glosas_en", [])[:3]
            saida.append(c)
        return {"resultados": saida}
    return _seguro(compacto)


@mcp.tool()
def kanji(literal: str) -> dict:
    """Um kanji no Kotoba: leituras on/kun, significados, nível, traços, radical."""
    from japones.fontes import kotoba
    return _seguro(lambda: kotoba.kanji(literal) or {"erro": "kanji não encontrado"})


@mcp.tool()
def consultas_kotoba(data: str | None = None) -> dict:
    """O que ele procurou no Kotoba num dia de estudo (padrão: hoje), e `sem_cartao`: as palavras que ele
    abriu e que não aparecem em nenhuma nota do Anki. Palavra consultada durante a produção é a que
    faltou — candidata a cartão no Passo 4 (é pista: o cartão pode existir noutra forma, たべます)."""
    from japones import painel
    d = date.fromisoformat(data) if data else dominio.dia_de_estudo()
    r = painel.kotoba_historico(1, ate=d)
    if "erro" in r:
        return r
    consultas = r["dias"][0]["consultas"] if r["dias"] else []
    return {"dia": d.isoformat(),
            "consultas": [f"{c['quando'][11:16]} {c['rotulo']}" + (" ✓cartão" if c.get("tem_cartao") else "")
                          for c in consultas],
            "sem_cartao": [f"{x['palavra']} ({x['leitura']})" if x["leitura"] else x["palavra"]
                           for x in r["sem_cartao"]],
            **({"aviso": r["aviso"]} if "aviso" in r else {})}


# ------------------------------------------------------------------ escrita

@mcp.tool()
def registrar_aula(data: str, tipo: str, texto_md: str, titulo: str | None = None,
                   dia_plano: int | None = None, inicio: str | None = None, minutos: int | None = None,
                   fase: int | None = None, semana: int | None = None,
                   verif_ok: int | None = None, verif_total: int | None = None,
                   prod_ok: int | None = None, prod_total: int | None = None) -> dict:
    """Grava a aula no banco E acrescenta `texto_md` no fim do diario.md (append, nunca reescreve).
    tipo: completa | parcial | sem_mesa. texto_md começa com '## AAAA-MM-DD (dia N do plano) — ...'."""
    if tipo not in ("completa", "parcial", "sem_mesa"):
        return {"erro": "tipo deve ser completa, parcial ou sem_mesa"}
    if not texto_md.strip().startswith(f"## {data}"):
        return {"erro": f"texto_md deve começar com '## {data}'"}
    con = _con()
    cur = con.execute("""INSERT INTO aula (data, dia_plano, tipo, titulo, fase, semana, inicio, minutos,
                           verif_ok, verif_total, prod_ok, prod_total, texto_md, origem)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'mcp')""",
                      (data, dia_plano, tipo, titulo, fase, semana, inicio, minutos,
                       verif_ok, verif_total, prod_ok, prod_total, texto_md.strip()))
    diario.acrescentar(texto_md)
    con.commit()
    con.close()
    return {"ok": True, "id": cur.lastrowid, "diario": "entrada acrescentada"}


@mcp.tool()
def registrar_trajeto(data: str, audio: bool | None = None, audio_fonte: str | None = None,
                      anki_cartoes: int | None = None, anki_minutos: float | None = None,
                      nota: str | None = None) -> dict:
    """Grava o trajeto de um dia. Sem números do Anki, busca na coleção sozinho. Não apaga o que já existe."""
    if anki_cartoes is None:
        from japones.fontes import anki
        dias = _seguro(anki.historico_por_dia, date.fromisoformat(data))
        if isinstance(dias, list):
            achado = next((x for x in dias if x["data"] == data), None)
            if achado:
                anki_cartoes, anki_minutos = achado["cartoes"], achado["minutos"]
    con = _con()
    con.execute("""INSERT INTO trajeto (data, anki_cartoes, anki_minutos, audio, audio_fonte, nota)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(data) DO UPDATE SET
                     anki_cartoes = COALESCE(excluded.anki_cartoes, trajeto.anki_cartoes),
                     anki_minutos = COALESCE(excluded.anki_minutos, trajeto.anki_minutos),
                     audio        = COALESCE(excluded.audio, trajeto.audio),
                     audio_fonte  = COALESCE(excluded.audio_fonte, trajeto.audio_fonte),
                     nota         = COALESCE(excluded.nota, trajeto.nota)""",
                (data, anki_cartoes, anki_minutos, None if audio is None else int(audio), audio_fonte, nota))
    con.commit()
    r = dict(con.execute("SELECT * FROM trajeto WHERE data = ?", (data,)).fetchone())
    con.close()
    return r


class Erro(BaseModel):
    bloco: str = Field(description="abertura | verificacao | producao | diagnostico | anki | outro")
    categoria: str = Field(description="ex.: particula:ni-de, forma-te, kana:vogal-longa (DESIGN §4.2)")
    escrito: str | None = Field(default=None, description="o que ele escreveu")
    correto: str | None = Field(default=None, description="a forma corrigida")
    porque: str | None = Field(default=None, description="a regra, em uma linha")


@mcp.tool()
def registrar_erros(data: str, erros: list[Erro]) -> dict:
    """Grava os erros corrigidos na aula, um por linha, com categoria."""
    con = _con()
    con.executemany("INSERT INTO erro (data, bloco, categoria, escrito, correto, porque) VALUES (?, ?, ?, ?, ?, ?)",
                    [(data, e.bloco, e.categoria, e.escrito, e.correto, e.porque) for e in erros])
    con.commit()
    con.close()
    return {"ok": True, "gravados": len(erros)}


@mcp.tool()
def abrir_padrao(categoria: str, descricao: str, aberto_em: str | None = None) -> dict:
    """Abre um padrão em vigília (um erro que se repete e pede aula de modelo, não mais cartões)."""
    con = _con()
    cur = con.execute("INSERT INTO padrao (categoria, descricao, aberto_em) VALUES (?, ?, ?)",
                      (categoria, descricao, aberto_em or dominio.dia_de_estudo().isoformat()))
    con.commit()
    con.close()
    return {"ok": True, "id": cur.lastrowid}


@mcp.tool()
def resolver_padrao(id: int, nota: str) -> dict:
    """Fecha um padrão — com a evidência de que ele parou de aparecer."""
    con = _con()
    n = con.execute("UPDATE padrao SET status = 'resolvido', resolvido_em = ?, nota = ? WHERE id = ?",
                    (dominio.dia_de_estudo().isoformat(), nota, id)).rowcount
    con.commit()
    con.close()
    return {"ok": bool(n)}


@mcp.tool()
def atualizar_padrao(id: int, descricao: str) -> dict:
    """Reescreve a descrição de um padrão aberto (nova evidência, regra refinada)."""
    con = _con()
    n = con.execute("UPDATE padrao SET descricao = ? WHERE id = ?", (descricao, id)).rowcount
    con.commit()
    con.close()
    return {"ok": bool(n)}


@mcp.tool()
def definir_nota(chave: str, valor: str) -> dict:
    """Grava uma nota chave/valor. 'lembrete_abertura' é o que a próxima aula cobra antes do conteúdo;
    valor vazio apaga."""
    con = _con()
    if valor.strip():
        con.execute("INSERT INTO nota (chave, valor, atualizado_em) VALUES (?, ?, datetime('now', 'localtime')) "
                    "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor, atualizado_em = excluded.atualizado_em",
                    (chave, valor))
    else:
        con.execute("DELETE FROM nota WHERE chave = ?", (chave,))
    con.commit()
    con.close()
    return {"ok": True}


# ------------------------------------------------------------------ exercícios (DESIGN §9)

PAINEL = "http://127.0.0.1:8787"


@mcp.tool()
def planejar_tipos(n: int = 25, semente: int | None = None) -> dict:
    """Sorteia a sequência de tipos da lição: variada, sem deixar tipo de fora (com n ≥ 9 entra cada tipo uma
    vez), no máximo 3 do mesmo tipo, com peso para o que ele erra mais e para o que não aparece há duas
    lições. 'producao' entra sempre, no fim. Padrão 25 (pedido dele em 23/10/2026), com a maior parte no
    conteúdo novo. O 'explicacao' não é sorteado: acrescente-o você, antes dos exercícios do conteúdo novo."""
    from japones import exercicios
    con = _con()
    r = exercicios.planejar_tipos(con, n, semente)
    con.close()
    return r


@mcp.tool()
def criar_licao(titulo: str, exercicios: list[dict], data: str | None = None) -> dict:
    """Cria a lição do dia no painel. Cada exercício: {tipo, bloco, enunciado, dados, explicacao, categoria,
    regra} no formato do DESIGN §9.2 (o `dados` leva o gabarito; o navegador nunca o recebe). Para texto
    japonês aceito em mais de uma grafia, liste todas nas `aceitas` (kanji e kana). `ouvir` grava o mp3 aqui
    (precisa de rede; ~2 s por frase): ditado {texto, aceitas} ou compreensão {texto, opcoes, correta}, com
    `fala` em kana se algum kanji tiver leitura ambígua. bloco: aquecimento | novo | verificacao | producao |
    revisao. `regra` (opcional) = slug do caderno que o exercício revisa: a 1ª resposta move a agenda dela.
    tipo 'explicacao' = o texto do conteúdo novo antes dos exercícios, sem resposta (botão Entendi):
    dados {"md": "..."} ou {"regra": "<slug>"} (usa a explicacao_md do caderno); bloco padrão 'novo';
    enunciado opcional (vira o título). `dica_erro` (opcional, até 200 caracteres): se a 1ª resposta sair
    errada, o painel mostra a dica em vez da resposta e pede uma 2ª tentativa (corrigiu = deslize; não
    corrigiu ou desistiu = lacuna). Escreva pelo checklist — tempo do verbo · partícula de cada substantivo ·
    forma do verbo pedida —, apontando onde olhar sem dar a resposta. Não vale em producao/explicacao; no
    digitar e no ditado não abre (fora das aceitas vai para você). Tudo ou nada: um exercício inválido
    recusa a lição com a mensagem."""
    from japones import exercicios as motor
    try:
        itens = [motor.ExercicioIn(**e) for e in exercicios]
        con = _con()
        lid = motor.criar_licao(con, titulo, itens, data)
        con.close()
    except (ValueError, TypeError) as e:
        return {"erro": str(e)}
    return {"ok": True, "id": lid, "exercicios": len(itens), "abrir": f"{PAINEL}/aula/{lid}"}


@mcp.tool()
def resultado_licao(id: int | None = None) -> dict:
    """O resultado da lição (padrão: a mais recente): por exercício, tipo, enunciado, a resposta dele,
    veredito e gabarito; e a lista dos 'revisar' que esperam correção sua (corrigir_exercicio). Só a 1ª
    resposta conta. Exercício que passou pela dica traz `autocorrigiu` (true = deslize, false = lacuna,
    null = dica pendente); a contagem separa os errados em `deslizes` e `lacunas`."""
    from japones import exercicios
    con = _con()
    lid = id or exercicios.licao_atual_id(con)
    l = exercicios.licao_renderizada(con, lid) if lid else None
    con.close()
    if not l:
        return {"erro": "nenhuma lição"}
    itens, contagem, pendentes = [], {"certo": 0, "errado": 0, "revisar": 0, "sem_resposta": 0, "deslizes": 0}, []
    for ex in l["exercicios"]:
        if ex["tipo"] == "explicacao":      # não é exercício: sem resposta, fora da contagem
            continue
        r = ex["resultado"]
        contagem[r["veredito"] if r else "sem_resposta"] += 1
        item = {"id": ex["id"], "tipo": ex["tipo"], "enunciado": ex["enunciado"][:120]}
        if r:
            item.update(veredito=r["veredito"], resposta=r["resposta"], gabarito=r["gabarito"])
            if r.get("dica"):       # enxuto: a chave só existe quando houve dica (§9.6)
                item["autocorrigiu"] = r["autocorrigiu"]
                contagem["deslizes"] += r["autocorrigiu"] is True
            if r["correcao"]:
                item["correcao"] = "(já corrigido)"
            elif r["veredito"] == "revisar":
                pendentes.append(ex["id"])
        itens.append(item)
    contagem["lacunas"] = contagem["errado"] - contagem["deslizes"]      # errado sem autocorreção
    return {"id": l["id"], "titulo": l["titulo"], "status": l["status"], "contagem": contagem,
            "revisar_pendentes": pendentes, "exercicios": itens}


@mcp.tool()
def corrigir_exercicio(exercicio_id: int, veredito: str, correcao: str) -> dict:
    """Fecha um 'revisar' (digitar fora do gabarito, produção): veredito 'certo' ou 'errado' e a correção
    em markdown (✅ certo / ❌ errado e por quê / ↪️ corrigido), que aparece para ele no painel."""
    from japones import exercicios
    con = _con()
    try:
        ok = exercicios.corrigir_revisao(con, exercicio_id, veredito, correcao)
    except ValueError as e:
        return {"erro": str(e)}
    finally:
        con.close()
    return {"ok": ok}


# ------------------------------------------------------------------ caderno de regras (DESIGN §13)

@mcp.tool()
def regras(vencidas: bool = True, limite: int = 10) -> list[dict]:
    """Regras de gramática do caderno, pela próxima revisão. vencidas=True: só as que vencem hoje ou já
    venceram (as que a lição deve revisar, com o campo `regra` nos exercícios); False: todas. Sem o texto
    da regra — para ele, regra(slug)."""
    con = _con()
    r = caderno.listar(con, dominio.dia_de_estudo(), vencidas, limite)
    con.close()
    return r


@mcp.tool()
def regra(slug: str) -> dict:
    """Uma regra do caderno inteira, com explicacao_md e a agenda (intervalo, próxima, acertos, erros)."""
    con = _con()
    r = caderno.obter(con, slug)
    con.close()
    return r or {"erro": f"a regra '{slug}' não está no caderno"}


@mcp.tool()
def salvar_regra(slug: str, titulo: str, categoria: str | None = None, explicacao_md: str | None = None,
                 ensinada_em: str | None = None) -> dict:
    """Cria ou atualiza uma regra do caderno pelo slug (ex. 'te-mo-ii'). Regra nova: primeira revisão amanhã.
    Regra existente: a agenda não é zerada e campo omitido não apaga o que já está gravado.
    categoria = a de erro associada (ex. 'gramatica:te-mo-ii'); ensinada_em = AAAA-MM-DD."""
    con = _con()
    try:
        return caderno.salvar(con, slug, titulo, categoria, explicacao_md, ensinada_em)
    except ValueError as e:
        return {"erro": str(e)}
    finally:
        con.close()


@mcp.tool()
def backup() -> dict:
    """Copia estudo.db (API de backup do SQLite, consistente mesmo em uso), diario.md, estado.json e
    plano/japao.md para ~/.local/share/japones/backup-progresso/. Rodar no fechamento de toda aula."""
    config.BACKUP.mkdir(parents=True, exist_ok=True)
    origem = sqlite3.connect(config.BANCO)
    destino = sqlite3.connect(config.BACKUP / "estudo.db")
    origem.backup(destino)
    destino.close()
    origem.close()
    copiados = ["estudo.db"]
    for arq in (config.DIARIO, config.ESTADO, config.RAIZ_REPO / "plano" / "japao.md"):
        if arq.exists():
            shutil.copy2(arq, config.BACKUP / arq.name)
            copiados.append(arq.name)
    return {"ok": True, "destino": str(config.BACKUP), "copiados": copiados}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
