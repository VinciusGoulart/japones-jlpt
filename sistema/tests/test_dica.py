"""Segunda tentativa com dica (DESIGN §9.6), agenda com deslize × lacuna (§13.2), aviso da madrugada
do hoje() e o esquema 5. Conteúdo de mentira: o banco é temporário (conftest) e nada é dado pessoal."""
import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from japones import config, db, dominio, exercicios as m, regras
from japones.exercicios import ExercicioIn as E

D = date(2026, 10, 23)
DICA = "Confira a partícula: o verbo é de movimento."


@pytest.fixture
def con(monkeypatch):
    for p in (config.BANCO, Path(str(config.BANCO) + "-wal"), Path(str(config.BANCO) + "-shm")):
        if p.exists():
            p.unlink()
    # o dia de estudo fica parado em D: a agenda depende dele
    monkeypatch.setattr(dominio, "dia_de_estudo", lambda agora=None: D)
    c = db.conectar()
    yield c
    c.close()


def _d(n: int) -> str:
    return (D + timedelta(days=n)).isoformat()


def _regra(con, slug="regra-a", intervalo=None):
    """Uma regra; com `intervalo`, madura: revisada pela última vez há `intervalo` dias, vencendo hoje."""
    regras.salvar(con, slug, f"Regra {slug}", dia=D)
    if intervalo is not None:
        con.execute("UPDATE regra SET intervalo = ?, proxima = ?, ultima_revisao = ? WHERE slug = ?",
                    (intervalo, _d(0), _d(-intervalo), slug))
        con.commit()
    return con.execute("SELECT id FROM regra WHERE slug = ?", (slug,)).fetchone()["id"]


def _agenda(con, slug="regra-a"):
    return dict(con.execute("SELECT intervalo, proxima, acertos, erros, deslizes FROM regra WHERE slug = ?",
                            (slug,)).fetchone())


def escolha(dica=DICA, regra=None, categoria="particula:ni-de"):
    return E(tipo="escolha", enunciado="学校＿行きます", categoria=categoria, explicacao="destino leva に",
             dados={"opcoes": ["に", "で", "を"], "correta": "に"}, dica_erro=dica, regra=regra)


ACHAR = E(tipo="achar_erro", enunciado="Ache o erro", categoria="particula:wo", dica_erro=DICA,
          dados={"segmentos": ["日本を", "行ったことが", "ありません"], "errado": 0, "correcao": "日本に"})


def _licao(con, *exs):
    lid = m.criar_licao(con, "t", list(exs), "2026-10-23")
    return lid, [e["id"] for e in m.licao_renderizada(con, lid)["exercicios"]]


def _res(con, lid, i=0):
    return m.licao_renderizada(con, lid)["exercicios"][i]["resultado"]


# ------------------------------------------------------------------ o fluxo (§9.6)

def test_primeira_errada_mostra_a_dica_sem_o_gabarito(con):
    lid, (eid,) = _licao(con, ACHAR)
    r = m.responder(con, eid, {"segmento": 1})
    assert r == {"veredito": "errado", "gabarito": "", "explicacao": None, "detalhe": {}, "contou": True, "dica": DICA}
    res = _res(con, lid)
    assert (res["dica"], res["segunda"], res["autocorrigiu"]) == (DICA, None, None)
    assert (res["gabarito"], res["explicacao"], res["detalhe"]) == ("", None, {})
    assert "日本に" not in json.dumps(m.licao_renderizada(con, lid), ensure_ascii=False)   # a correção não vaza
    # o erro da 1ª já está na tabela, ainda sem a marca de deslize
    assert [tuple(e) for e in con.execute("SELECT categoria, deslize, exercicio_id FROM erro")] == [("particula:wo", 0, eid)]


def test_segunda_certa_e_deslize_mas_o_placar_fica_com_a_primeira(con):
    from japones import mcp_server
    lid, (eid,) = _licao(con, escolha())
    m.responder(con, eid, {"opcao": "で"})
    r2 = m.responder(con, eid, {"opcao": "に"})
    assert (r2["veredito"], r2["contou"], r2["autocorrigiu"], r2["gabarito"]) == ("certo", False, True, "に")
    res = _res(con, lid)
    assert res["veredito"] == "errado" and res["resposta"] == {"opcao": "で"}      # a 1ª é a que conta
    assert res["segunda"] == {"resposta": {"opcao": "に"}, "veredito": "certo", "detalhe": {}}
    assert res["autocorrigiu"] is True and res["gabarito"] == "に" and res["explicacao"] == "destino leva に"
    assert con.execute("SELECT deslize FROM erro").fetchone()[0] == 1
    assert [tuple(x) for x in con.execute("SELECT veredito, apos_dica FROM resposta ORDER BY id")] == [
        ("errado", 0), ("certo", 1)]
    assert m.resumo_licoes(con)[0]["errados"] == 1 and m.resumo_licoes(con)[0]["certos"] == 0

    rl = mcp_server.resultado_licao(lid)
    assert rl["exercicios"][0]["autocorrigiu"] is True
    assert rl["contagem"] == {"certo": 0, "errado": 1, "revisar": 0, "sem_resposta": 0, "deslizes": 1, "lacunas": 0}


def test_segunda_errada_e_lacuna(con):
    lid, (eid,) = _licao(con, escolha())
    m.responder(con, eid, {"opcao": "で"})
    r2 = m.responder(con, eid, {"opcao": "を"})
    assert (r2["veredito"], r2["autocorrigiu"]) == ("errado", False)
    res = _res(con, lid)
    assert res["autocorrigiu"] is False and res["segunda"]["resposta"] == {"opcao": "を"}
    assert con.execute("SELECT deslize FROM erro").fetchone()[0] == 0


def test_desistir_e_lacuna_e_mostra_a_correcao_da_primeira(con):
    from fastapi import HTTPException
    from japones import api, mcp_server
    lid, (eid, outro) = _licao(con, ACHAR, escolha(dica=None))
    with pytest.raises(HTTPException) as e:                          # ainda não respondeu: nada a desistir
        api.desistir(eid)
    assert e.value.status_code == 409
    m.responder(con, eid, {"segmento": 2})
    r = api.desistir(eid)
    assert r == {"veredito": "errado", "gabarito": "日本を → 日本に", "explicacao": None,
                 "detalhe": {"errado": 0, "correcao": "日本に"}, "contou": False, "autocorrigiu": False}
    res = _res(con, lid)
    assert (res["segunda"], res["autocorrigiu"], res["detalhe"]) == ({"desistiu": True}, False, {"errado": 0, "correcao": "日本に"})
    with pytest.raises(HTTPException) as e:                          # não se desiste duas vezes
        api.desistir(eid)
    assert e.value.status_code == 409
    with pytest.raises(HTTPException) as e:
        api.desistir(9999)
    assert e.value.status_code == 404
    rl = mcp_server.resultado_licao(lid)
    assert rl["exercicios"][0]["autocorrigiu"] is False and "autocorrigiu" not in rl["exercicios"][1]
    assert (rl["contagem"]["deslizes"], rl["contagem"]["lacunas"]) == (0, 1)


def test_depois_da_dica_o_praticar_de_novo_segue_como_antes(con):
    lid, (eid,) = _licao(con, escolha())
    m.responder(con, eid, {"opcao": "で"})
    m.responder(con, eid, {"opcao": "を"})                           # a 2ª tentativa
    r3 = m.responder(con, eid, {"opcao": "に"})                      # treino
    assert (r3["contou"], "autocorrigiu" in r3, "dica" in r3) == (False, False, False)
    assert [x[0] for x in con.execute("SELECT apos_dica FROM resposta ORDER BY id")] == [0, 1, 0]
    assert _res(con, lid)["autocorrigiu"] is False                   # o treino não reescreve a 2ª tentativa


def test_sem_dica_erro_o_comportamento_e_o_antigo(con):
    lid, (eid,) = _licao(con, escolha(dica=None))
    r1 = m.responder(con, eid, {"opcao": "で"})
    assert r1 == {"veredito": "errado", "gabarito": "に", "explicacao": "destino leva に", "detalhe": {}, "contou": True}
    r2 = m.responder(con, eid, {"opcao": "に"})
    assert (r2["contou"], "autocorrigiu" in r2) == (False, False)
    res = _res(con, lid)
    assert (res["dica"], res["segunda"], res["autocorrigiu"], res["gabarito"]) == (None, None, None, "に")
    assert [x[0] for x in con.execute("SELECT apos_dica FROM resposta")] == [0, 0]


def test_primeira_certa_nao_abre_dica(con):
    lid, (eid,) = _licao(con, escolha())
    assert "dica" not in m.responder(con, eid, {"opcao": "に"})
    assert _res(con, lid)["dica"] is None


def test_revisar_fechado_como_errado_pelo_tutor_nao_abre_dica(con):
    dig = E(tipo="digitar", enunciado="Escreva", dados={"aceitas": ["学校に行きます"]}, dica_erro=DICA)
    lid, (eid,) = _licao(con, dig)
    assert "dica" not in m.responder(con, eid, {"texto": "学校で行きます"})      # revisar: vai para o tutor
    m.corrigir_revisao(con, eid, "errado", "❌ destino leva に")
    res = _res(con, lid)
    assert (res["veredito"], res["dica"], res["autocorrigiu"]) == ("errado", None, None)
    assert m.responder(con, eid, {"texto": "学校に行きます"})["contou"] is False
    assert [x[0] for x in con.execute("SELECT apos_dica FROM resposta")] == [0, 0]


def test_dica_pendente_nao_segura_a_licao(con):
    lid, (eid,) = _licao(con, escolha())
    m.responder(con, eid, {"opcao": "で"})
    assert m.resumo_licoes(con)[0]["status"] == "concluida"


# ------------------------------------------------------------------ validação do dica_erro

@pytest.mark.parametrize("ex,msg", [
    (escolha(dica=""), "texto não vazio"),
    (escolha(dica="   "), "texto não vazio"),
    (escolha(dica="x" * 201), "201 caracteres; o máximo é 200"),
    (E(tipo="producao", bloco="producao", enunciado="3 frases", dados={"minimo": 3}, dica_erro=DICA), "não vale para producao"),
    (E(tipo="explicacao", dados={"md": "texto"}, dica_erro=DICA), "não vale para explicacao"),
])
def test_dica_invalida_recusa_a_licao_inteira(con, ex, msg):
    with pytest.raises(ValueError, match=f"exercício 2 .*{msg}"):
        m.criar_licao(con, "t", [escolha(), ex])
    assert con.execute("SELECT COUNT(*) FROM licao").fetchone()[0] == 0


def test_dica_de_200_caracteres_passa_e_e_gravada_sem_espacos_nas_pontas(con):
    lid, (eid,) = _licao(con, escolha(dica=" " + "x" * 200 + " "))
    assert con.execute("SELECT dica_erro FROM exercicio WHERE id = ?", (eid,)).fetchone()[0] == "x" * 200


def test_criar_licao_pelo_mcp_com_dica(con):
    from japones import mcp_server
    ok = mcp_server.criar_licao("t", [{"tipo": "escolha", "enunciado": "x", "dica_erro": DICA,
                                       "dados": {"opcoes": ["a", "b"], "correta": "a"}}])
    assert ok["ok"] is True
    assert "erro" in mcp_server.criar_licao("t", [{"tipo": "escolha", "enunciado": "x", "dica_erro": 5,
                                                   "dados": {"opcoes": ["a", "b"], "correta": "a"}}])
    assert "erro" in mcp_server.criar_licao("t", [{"tipo": "escolha", "enunciado": "x", "dica_erro": "",
                                                   "dados": {"opcoes": ["a", "b"], "correta": "a"}}])


def test_a_dica_nao_vai_no_render(con):
    lid, _ = _licao(con, escolha())
    assert DICA not in json.dumps(m.licao_renderizada(con, lid), ensure_ascii=False)


# ------------------------------------------------------------------ agenda: deslize × lacuna (§13.2)

def test_deslize_recua_um_degrau_12_para_5(con):
    _regra(con, intervalo=12)
    lid, (eid,) = _licao(con, escolha(regra="regra-a"))
    m.responder(con, eid, {"opcao": "で"})
    assert _agenda(con) == {"intervalo": 1, "proxima": _d(1), "acertos": 0, "erros": 1, "deslizes": 0}   # lacuna na hora
    m.responder(con, eid, {"opcao": "に"})
    assert _agenda(con) == {"intervalo": 5, "proxima": _d(5), "acertos": 0, "erros": 0, "deslizes": 1}


def test_lacuna_volta_ao_zero_12_para_1(con):
    _regra(con, intervalo=12)
    lid, (a,) = _licao(con, escolha(regra="regra-a"))
    m.responder(con, a, {"opcao": "で"})
    m.desistir(con, a)
    assert _agenda(con) == {"intervalo": 1, "proxima": _d(1), "acertos": 0, "erros": 1, "deslizes": 0}


def test_lacuna_sem_dica_e_a_de_sempre(con):
    _regra(con, intervalo=30)
    lid, (eid,) = _licao(con, escolha(dica=None, regra="regra-a"))
    m.responder(con, eid, {"opcao": "で"})
    m.responder(con, eid, {"opcao": "に"})                           # treino: não é deslize
    assert _agenda(con) == {"intervalo": 1, "proxima": _d(1), "acertos": 0, "erros": 1, "deslizes": 0}


@pytest.mark.parametrize("ordem", [
    "A1 A2 B1 B2",      # o fluxo normal: cada dica resolvida na hora
    "B1 B2 A1 A2",
    "A1 B1 B2 A2",      # pulou de exercício com a dica de A pendente: a lacuna de B não pode ser apagada
    "A1 B1 A2 B2",
])
def test_lacuna_no_dia_ganha_do_deslize_em_qualquer_ordem(con, ordem):
    _regra(con, intervalo=12)
    lid, (a, b) = _licao(con, escolha(regra="regra-a"), escolha(regra="regra-a"))
    passos = {"A1": lambda: m.responder(con, a, {"opcao": "で"}), "A2": lambda: m.responder(con, a, {"opcao": "に"}),
              "B1": lambda: m.responder(con, b, {"opcao": "で"}), "B2": lambda: m.desistir(con, b)}
    for p in ordem.split():
        passos[p]()
    assert _agenda(con) == {"intervalo": 1, "proxima": _d(1), "acertos": 0, "erros": 1, "deslizes": 1}


def test_dois_deslizes_no_dia_recuam_um_degrau_so(con):
    _regra(con, intervalo=12)
    lid, (a, b) = _licao(con, escolha(regra="regra-a"), escolha(regra="regra-a"))
    for eid in (a, b):
        m.responder(con, eid, {"opcao": "で"})
        m.responder(con, eid, {"opcao": "に"})
    assert _agenda(con) == {"intervalo": 5, "proxima": _d(5), "acertos": 0, "erros": 0, "deslizes": 2}


def test_deslize_recua_do_intervalo_de_antes_do_dia(con):
    """Um acerto mais cedo no mesmo dia fez a regra crescer (12 → 30); o deslize recua dos 12."""
    _regra(con, intervalo=12)
    lid, (a, b) = _licao(con, escolha(regra="regra-a"), escolha(regra="regra-a"))
    m.responder(con, a, {"opcao": "に"})
    assert _agenda(con)["intervalo"] == 30
    m.responder(con, b, {"opcao": "で"})
    m.responder(con, b, {"opcao": "に"})
    assert _agenda(con) == {"intervalo": 5, "proxima": _d(5), "acertos": 1, "erros": 0, "deslizes": 1}


def test_acerto_depois_do_deslize_no_mesmo_dia_nao_faz_crescer(con):
    _regra(con, intervalo=12)
    lid, (a, b) = _licao(con, escolha(regra="regra-a"), escolha(regra="regra-a"))
    m.responder(con, a, {"opcao": "で"})
    m.responder(con, a, {"opcao": "に"})
    m.responder(con, b, {"opcao": "に"})
    assert _agenda(con) == {"intervalo": 5, "proxima": _d(5), "acertos": 1, "erros": 0, "deslizes": 1}


@pytest.mark.parametrize("antes,depois", [(30, 12), (60, 24), (5, 2), (2, 1), (0, 1)])
def test_degraus_do_recuo(antes, depois):
    assert regras.recuar(antes) == depois


def test_deslize_depois_que_a_agenda_andou_so_mexe_nos_contadores(con):
    rid = _regra(con, intervalo=12)
    regras.agendar(con, rid, "errado", D)
    regras.agendar(con, rid, "certo", D + timedelta(days=1))         # outro dia: a agenda andou
    antes = _agenda(con)
    regras.deslize(con, rid, D)
    depois = _agenda(con)
    assert (depois["intervalo"], depois["proxima"]) == (antes["intervalo"], antes["proxima"])
    assert (depois["erros"], depois["deslizes"]) == (0, 1)


def test_deslize_com_intervalo_dia_nulo_vale_como_lacuna(con):
    """Regra com evento no dia antes do esquema 5 (intervalo_dia nulo): na dúvida, o lado seguro."""
    rid = _regra(con, intervalo=12)
    regras.agendar(con, rid, "errado", D)
    con.execute("UPDATE regra SET intervalo_dia = NULL WHERE id = ?", (rid,))
    regras.deslize(con, rid, D)
    assert _agenda(con) == {"intervalo": 1, "proxima": _d(1), "acertos": 0, "erros": 0, "deslizes": 1}


def test_caderno_traz_deslizes_e_deslize_nao_deixa_fragil(con):
    from japones import api
    _regra(con, intervalo=12)
    lid, (eid,) = _licao(con, escolha(regra="regra-a"))
    m.responder(con, eid, {"opcao": "で"})
    m.responder(con, eid, {"opcao": "に"})
    r = api.listar_regras()[0]
    assert (r["deslizes"], r["erros"], r["acertos"], r["status"]) == (1, 0, 0, "em_dia")


# ------------------------------------------------------------------ erros()

def test_erros_traz_deslize_por_linha_e_por_categoria(con):
    from japones import mcp_server
    lid, (a, b, c) = _licao(con, escolha(), escolha(), escolha(categoria="forma-te"))
    for eid, segunda in ((a, "に"), (b, "を"), (c, "に")):
        m.responder(con, eid, {"opcao": "で"})
        m.responder(con, eid, {"opcao": segunda})
    r = mcp_server.erros()
    assert r["por_categoria"] == {"particula:ni-de": 2, "forma-te": 1}
    assert r["deslizes_por_categoria"] == {"particula:ni-de": 1, "forma-te": 1}
    assert sorted(e["deslize"] for e in r["erros"]) == [False, True, True]


# ------------------------------------------------------------------ hoje(): o aviso da madrugada

@pytest.mark.parametrize("agora,avisa", [
    (datetime(2026, 10, 27, 2, 0), True),       # terça 02:00: ele trabalha na terça
    (datetime(2026, 10, 26, 1, 0), True),       # segunda 01:00 (sessão de domingo à noite)
    (datetime(2026, 10, 23, 3, 59), True),      # sexta 03:59
    (datetime(2026, 10, 24, 2, 0), False),      # sábado 02:00 (sessão de sexta à noite): não trabalha
    (datetime(2026, 10, 25, 1, 30), False),     # domingo
    (datetime(2026, 10, 27, 0, 59), False),     # antes da 1h
    (datetime(2026, 10, 27, 4, 0), False),      # depois das 04:00 já é outro dia de estudo
    (datetime(2026, 10, 27, 21, 0), False),     # a hora de sempre
])
def test_hoje_avisa_aula_so_de_revisao_na_madrugada_de_dia_util(monkeypatch, agora, avisa):
    from japones import mcp_server as mcp
    for p in (config.BANCO,):
        if p.exists():
            p.unlink()
    monkeypatch.setattr(mcp, "_agora", lambda: agora)
    monkeypatch.setattr(mcp, "_resumo_trello", lambda *a: {"erro": "fora"})
    monkeypatch.setattr(mcp, "_resumo_anki", lambda: {"erro": "fora"})
    h = mcp.hoje()
    assert (mcp.AVISO_MADRUGADA in h["avisos"]) is avisa
    assert h["dia_de_estudo"] == dominio.dia_de_estudo(agora).isoformat()     # o resto segue a regra das 04:00
    assert mcp.AVISO_MADRUGADA.startswith("Depois da 1h em véspera de trabalho: aula só de revisão")


# ------------------------------------------------------------------ esquema 5

def test_esquema_5_acrescenta_as_colunas_sem_perder_nada(tmp_path):
    caminho = tmp_path / "v4.db"
    c = sqlite3.connect(caminho)
    c.executescript(db._DDL.read_text() + db._DDL2.read_text() + db._DDL3.read_text() + db._DDL4.read_text())
    c.execute("PRAGMA user_version = 4")
    c.execute("INSERT INTO licao (id, data, titulo) VALUES (1, '2026-10-22', 'antiga')")
    c.execute("INSERT INTO exercicio (id, licao_id, ordem, bloco, tipo, enunciado, dados) "
              "VALUES (7, 1, 1, 'verificacao', 'escolha', 'x', '{\"opcoes\": [\"a\", \"b\"], \"correta\": \"a\"}')")
    c.execute("INSERT INTO resposta (exercicio_id, resposta, veredito) VALUES (7, '{\"opcao\": \"b\"}', 'errado')")
    c.execute("INSERT INTO erro (data, bloco, categoria) VALUES ('2026-10-22', 'verificacao', 'outro')")
    c.execute("INSERT INTO regra (slug, titulo, intervalo, erros) VALUES ('a', 'A', 12, 2)")
    c.commit()
    c.close()

    novo = db.conectar(caminho)
    assert novo.execute("PRAGMA user_version").fetchone()[0] == db.ESQUEMA_ATUAL == 5
    assert dict(novo.execute("SELECT dica_erro FROM exercicio WHERE id = 7").fetchone()) == {"dica_erro": None}
    assert novo.execute("SELECT apos_dica FROM resposta").fetchone()[0] == 0
    assert tuple(novo.execute("SELECT exercicio_id, deslize FROM erro").fetchone()) == (None, 0)
    assert tuple(novo.execute("SELECT intervalo, erros, deslizes, intervalo_dia, lacunas_dia FROM regra").fetchone()) == (
        12, 2, 0, None, 0)
    assert novo.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):                      # o CHECK novo vale
        novo.execute("INSERT INTO resposta (exercicio_id, resposta, veredito, apos_dica) VALUES (7, '{}', 'certo', 2)")
    novo.execute("UPDATE erro SET exercicio_id = 7")
    novo.execute("DELETE FROM licao WHERE id = 1")                   # a cascata apaga o exercício...
    assert tuple(novo.execute("SELECT exercicio_id FROM erro").fetchone()) == (None,)   # ...e o erro fica
    novo.commit()
    novo.close()
    db.conectar(caminho).close()                                     # conectar de novo não refaz nada
