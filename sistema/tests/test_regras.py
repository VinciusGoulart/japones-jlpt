"""Caderno de regras (DESIGN §13): agenda, o tipo explicacao, o campo regra, o importador e o esquema 4.
O conteúdo das regras aqui é de mentira, em português: o caderno de verdade é do tutor."""
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from japones import config, db, dominio, exercicios as m, regras
from japones.exercicios import ExercicioIn as E

D = date(2026, 10, 23)


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


def _nova(con, slug="regra-a", **kw):
    regras.salvar(con, slug, kw.pop("titulo", f"Regra {slug}"), dia=D, **kw)
    return con.execute("SELECT id FROM regra WHERE slug = ?", (slug,)).fetchone()["id"]


def _agenda(con, slug="regra-a"):
    r = con.execute("SELECT intervalo, proxima, acertos, erros, ultima_revisao, ultima_falha FROM regra WHERE slug = ?",
                    (slug,)).fetchone()
    return dict(r)


def _d(n: int) -> str:
    return (D + timedelta(days=n)).isoformat()


# ------------------------------------------------------------------ agenda (§13.2)

def test_regra_nova_nasce_para_amanha(con):
    _nova(con)
    a = _agenda(con)
    assert (a["intervalo"], a["proxima"], a["acertos"], a["erros"]) == (0, _d(1), 0, 0)


def test_erro_segura_a_regra_para_amanha(con):
    rid = _nova(con)
    regras.agendar(con, rid, "errado", D)
    a = _agenda(con)
    assert (a["intervalo"], a["proxima"], a["erros"], a["ultima_falha"], a["ultima_revisao"]) == (1, _d(1), 1, _d(0), _d(0))


def test_acertos_em_dias_diferentes_seguem_2_5_12_30_60_e_param_no_teto(con):
    rid = _nova(con)
    dia, vistos = D, []
    for _ in range(6):
        regras.agendar(con, rid, "certo", dia)
        a = _agenda(con)
        vistos.append(a["intervalo"])
        assert a["proxima"] == (dia + timedelta(days=int(a["intervalo"]))).isoformat()
        dia = date.fromisoformat(a["proxima"])
    assert vistos == [2, 5, 12, 30, 60, 60]
    assert _agenda(con)["acertos"] == 6


def test_varios_acertos_no_mesmo_dia_contam_uma_vez(con):
    rid = _nova(con)
    for _ in range(3):
        regras.agendar(con, rid, "certo", D)
    a = _agenda(con)
    assert (a["intervalo"], a["proxima"], a["acertos"]) == (2, _d(2), 3)


def test_erro_no_dia_impede_o_acerto_de_crescer(con):
    rid = _nova(con)
    regras.agendar(con, rid, "certo", D - timedelta(days=5))          # já estava em 2
    regras.agendar(con, rid, "errado", D)
    regras.agendar(con, rid, "certo", D)
    a = _agenda(con)
    assert (a["intervalo"], a["proxima"], a["acertos"], a["erros"]) == (1, _d(1), 2, 1)


# ------------------------------------------------------------------ o campo `regra` nos exercícios

ESCOLHA = dict(tipo="escolha", enunciado="Qual?", dados={"opcoes": ["a", "b"], "correta": "a"}, categoria="gramatica:a")


def test_criar_licao_com_regra_grava_e_a_primeira_resposta_agenda(con):
    rid = _nova(con)
    lid = m.criar_licao(con, "t", [E(**ESCOLHA, regra="regra-a")], "2026-10-23")
    ex = m.licao_renderizada(con, lid)["exercicios"][0]
    assert con.execute("SELECT regra_id FROM exercicio WHERE id = ?", (ex["id"],)).fetchone()[0] == rid
    m.responder(con, ex["id"], {"opcao": "a"})
    m.responder(con, ex["id"], {"opcao": "b"})                         # treino: não conta
    a = _agenda(con)
    assert (a["intervalo"], a["proxima"], a["acertos"], a["erros"]) == (2, _d(2), 1, 0)


def test_criar_licao_com_regra_desconhecida_recusa_tudo(con):
    with pytest.raises(ValueError, match="exercício 2 \\(escolha\\).*'nao-existe' não está no caderno"):
        m.criar_licao(con, "t", [E(**ESCOLHA), E(**ESCOLHA, regra="nao-existe")])
    assert con.execute("SELECT COUNT(*) FROM licao").fetchone()[0] == 0


def test_revisar_agenda_so_quando_o_tutor_fecha_e_so_uma_vez(con):
    _nova(con)
    dig = E(tipo="digitar", enunciado="Escreva", dados={"aceitas": ["abc"]}, regra="regra-a")
    lid = m.criar_licao(con, "t", [dig], "2026-10-23")
    ex = m.licao_renderizada(con, lid)["exercicios"][0]
    assert m.responder(con, ex["id"], {"texto": "abd"})["veredito"] == "revisar"
    assert _agenda(con)["erros"] == 0                                  # ainda com o tutor
    m.corrigir_revisao(con, ex["id"], "errado", "❌ era abc")
    m.corrigir_revisao(con, ex["id"], "certo", "reescrevi a correção")   # não conta de novo
    a = _agenda(con)
    assert (a["intervalo"], a["proxima"], a["acertos"], a["erros"]) == (1, _d(1), 0, 1)


# ------------------------------------------------------------------ o tipo explicacao

def test_explicacao_fica_fora_do_placar_e_do_concluida(con):
    from japones import mcp_server
    _nova(con, explicacao_md="**Regra A**: texto de teste\n\n- item")
    lid = m.criar_licao(con, "t", [
        E(tipo="explicacao", enunciado="Conteúdo de hoje", dados={"md": "# Título\n\ntexto **forte**"}),
        E(**ESCOLHA),
        E(tipo="explicacao", dados={"regra": "regra-a"}),
    ], "2026-10-23")
    l = m.licao_renderizada(con, lid)
    exp, esc, exp2 = l["exercicios"]
    assert (exp["bloco"], exp["tipo"], exp["render"]) == ("novo", "explicacao",
                                                         {"md": "# Título\n\ntexto **forte**", "titulo": None, "regra": None})
    assert exp2["render"] == {"md": "**Regra A**: texto de teste\n\n- item", "titulo": "Regra regra-a", "regra": "regra-a"}
    assert esc["bloco"] == "verificacao"                               # o padrão dos outros tipos não mudou
    assert m.resumo_licoes(con)[0]["total"] == 1

    with pytest.raises(ValueError, match="não tem resposta"):
        m.responder(con, exp["id"], {})
    m.responder(con, esc["id"], {"opcao": "b"})
    assert m.resumo_licoes(con)[0]["status"] == "concluida"            # as explicações não seguram a lição
    assert con.execute("SELECT COUNT(*) FROM resposta").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM erro").fetchone()[0] == 1

    r = mcp_server.resultado_licao(lid)
    assert [x["tipo"] for x in r["exercicios"]] == ["escolha"]
    assert r["contagem"] == {"certo": 0, "errado": 1, "revisar": 0, "sem_resposta": 0, "deslizes": 0, "lacunas": 1}


def test_explicacao_por_regra_mostra_a_versao_atual_do_caderno(con):
    _nova(con, explicacao_md="versão 1")
    lid = m.criar_licao(con, "t", [E(tipo="explicacao", dados={"regra": "regra-a"})], "2026-10-23")
    regras.salvar(con, "regra-a", "Regra A", explicacao_md="versão 2", dia=D)
    assert m.licao_renderizada(con, lid)["exercicios"][0]["render"]["md"] == "versão 2"


@pytest.mark.parametrize("dados,msg", [
    ({"regra": "nao-existe"}, "não está no caderno"),
    ({"regra": "sem-texto"}, "não tem explicacao_md"),
    ({"md": "a", "regra": "sem-texto"}, "um dos dois"),
    ({}, "um dos dois"),
    ({"md": "  "}, "não vazio"),
])
def test_explicacao_invalida_recusa_a_licao(con, dados, msg):
    _nova(con, "sem-texto")
    with pytest.raises(ValueError, match=msg):
        m.criar_licao(con, "t", [E(**ESCOLHA), E(tipo="explicacao", dados=dados)])
    assert con.execute("SELECT COUNT(*) FROM licao").fetchone()[0] == 0


def test_outros_tipos_continuam_exigindo_enunciado(con):
    with pytest.raises(ValueError, match="falta 'enunciado'"):
        m.criar_licao(con, "t", [E(tipo="escolha", dados={"opcoes": ["a", "b"], "correta": "a"})])


def test_api_recusa_resposta_de_explicacao(con):
    from fastapi import HTTPException
    from japones import api
    lid = m.criar_licao(con, "t", [E(tipo="explicacao", dados={"md": "x"}), E(**ESCOLHA)], "2026-10-23")
    exp_id = m.licao_renderizada(con, lid)["exercicios"][0]["id"]
    with pytest.raises(HTTPException) as e:
        api.responder(exp_id, {}, None)
    assert e.value.status_code == 400


# ------------------------------------------------------------------ sorteio com 25

def test_sorteio_de_25_fecha_a_conta_sem_explicacao(con):
    from japones import mcp_server
    for semente in range(5):
        p = m.planejar_tipos(con, n=25, semente=semente)
        assert len(p["tipos"]) == 25 and p["tipos"][-1] == "producao" and p["tipos"].count("producao") == 1
        assert set(p["tipos"]) == set(m.TIPOS) and "explicacao" not in p["pesos"]
        assert max(p["tipos"].count(t) for t in m.TIPOS) <= 3
    assert len(mcp_server.planejar_tipos(semente=1)["tipos"]) == 25    # o padrão da ferramenta


# ------------------------------------------------------------------ importador (§13.3)

def _item(slug, ensinada=None, **kw):
    return {"slug": slug, "titulo": f"Regra {slug}", "categoria": f"gramatica:{slug}", "ensinada_em": ensinada,
            "explicacao_md": f"texto de {slug}", **kw}


def test_importador_espalha_5_por_dia_das_mais_antigas_para_as_novas(con):
    _nova(con, "ja-agendada")
    regras.agendar(con, con.execute("SELECT id FROM regra").fetchone()[0], "certo", D)
    antes = _agenda(con, "ja-agendada")
    # 11 com data, fora de ordem, e uma sem data (vai para o fim); a já agendada vem no arquivo também
    itens = [_item(f"r{i:02d}", _d(-30 + (i * 7) % 11)) for i in range(11)] + [_item("sem-data"),
                                                                               _item("ja-agendada", titulo="Novo título")]
    r = regras.importar(con, itens, dia=D)
    assert (r["lidas"], r["novas"], r["atualizadas"], r["agendadas"], r["de"], r["ate"]) == (13, 12, 1, 12, _d(0), _d(2))

    ordem = [(x["slug"], x["proxima"]) for x in con.execute(
        "SELECT slug, proxima FROM regra WHERE slug != 'ja-agendada' ORDER BY proxima, ensinada_em IS NULL, ensinada_em")]
    assert [p for _, p in ordem] == [_d(0)] * 5 + [_d(1)] * 5 + [_d(2)] * 2
    datas = [con.execute("SELECT ensinada_em FROM regra WHERE slug = ?", (s,)).fetchone()[0] for s, _ in ordem]
    assert datas[:-1] == sorted(datas[:-1]) and ordem[-1][0] == "sem-data"

    depois = _agenda(con, "ja-agendada")
    assert depois == antes                                             # a agenda não é zerada
    assert regras.obter(con, "ja-agendada")["titulo"] == "Novo título"

    # reimportar é idempotente: nada é reagendado
    proximas = dict(con.execute("SELECT slug, proxima FROM regra").fetchall())
    r2 = regras.importar(con, itens, dia=D + timedelta(days=3))
    assert (r2["novas"], r2["agendadas"]) == (0, 0)
    assert dict(con.execute("SELECT slug, proxima FROM regra").fetchall()) == proximas


def test_importador_nao_apaga_campo_ausente(con):
    regras.importar(con, [_item("a", _d(-3))], dia=D)
    regras.importar(con, [{"slug": "a", "titulo": "Só o título"}], dia=D)
    r = regras.obter(con, "a")
    assert (r["titulo"], r["explicacao_md"], r["ensinada_em"], r["categoria"]) == ("Só o título", "texto de a", _d(-3), "gramatica:a")


@pytest.mark.parametrize("itens,msg", [
    ([_item("a"), _item("b"), {"slug": "c"}], "regra 3: falta 'titulo'"),
    ([_item("a"), _item("com espaço")], "regra 2: 'slug'"),
    ([_item("a", "23/10/2026")], "regra 1: 'ensinada_em' é AAAA-MM-DD"),
    ([_item("a"), _item("a")], "slug repetido"),
    ({"x": 1}, "o arquivo é uma lista"),
])
def test_importador_tudo_ou_nada(con, itens, msg):
    with pytest.raises(ValueError, match=msg):
        regras.importar(con, itens, dia=D)
    assert con.execute("SELECT COUNT(*) FROM regra").fetchone()[0] == 0


def test_importador_pela_linha_de_comando(con, tmp_path, capsys):
    arq = tmp_path / "regras.json"
    arq.write_text(json.dumps({"regras": [_item(f"r{i}", _d(-i)) for i in range(7)]}, ensure_ascii=False))
    assert regras.main(["importar", str(arq), "--por-dia", "3"]) == 0
    saida = json.loads(capsys.readouterr().out)
    assert (saida["novas"], saida["de"], saida["ate"]) == (7, _d(0), _d(2))
    assert regras.obter(con, "r6")["proxima"] == _d(0)                 # a mais antiga primeiro
    arq.write_text("[{")
    assert regras.main(["importar", str(arq)]) == 1


# ------------------------------------------------------------------ MCP e API

def test_ferramentas_mcp_do_caderno(con):
    from japones import mcp_server as mcp
    r = mcp.salvar_regra("a", "Regra A", categoria="gramatica:a", explicacao_md="texto", ensinada_em=_d(-2))
    assert r == {"ok": True, "slug": "a", "nova": True, "proxima": _d(1)}
    regras.importar(con, [_item("b", _d(-9))], dia=D)                  # vence hoje
    assert [x["slug"] for x in mcp.regras()] == ["b"]
    assert [x["slug"] for x in mcp.regras(vencidas=False)] == ["b", "a"]
    assert set(mcp.regras()[0]) == {"slug", "titulo", "ensinada_em", "proxima", "intervalo", "acertos", "erros"}

    assert mcp.salvar_regra("a", "Regra A revista")["nova"] is False
    a = mcp.regra("a")
    assert (a["titulo"], a["explicacao_md"], a["proxima"]) == ("Regra A revista", "texto", _d(1))
    assert "erro" in mcp.regra("nao-existe")
    assert "erro" in mcp.salvar_regra("com espaço", "x")


def test_hoje_traz_as_regras_vencidas(con, monkeypatch):
    from japones import mcp_server as mcp
    monkeypatch.setattr(mcp, "_resumo_trello", lambda *a: {"erro": "fora"})
    monkeypatch.setattr(mcp, "_resumo_anki", lambda: {"erro": "fora"})
    regras.importar(con, [_item(f"r{i}", _d(-i)) for i in range(8)], dia=D - timedelta(days=1))
    h = mcp.hoje()
    assert h["regras_vencidas"]["total"] == 8
    assert len(h["regras_vencidas"]["proximas"]) == 5


def test_api_regras_com_status(con):
    from japones import api
    for slug in ("vencida", "fragil", "em-dia", "sem-agenda"):
        _nova(con, slug, explicacao_md=f"texto {slug}")
    rid = {s: i for s, i in con.execute("SELECT slug, id FROM regra")}
    con.execute("UPDATE regra SET proxima = ? WHERE slug = 'vencida'", (_d(-2),))
    con.execute("UPDATE regra SET erros = 2, acertos = 1, proxima = ? WHERE id = ?", (_d(3), rid["fragil"]))
    con.execute("UPDATE regra SET proxima = NULL WHERE slug = 'sem-agenda'")
    con.commit()
    lista = api.listar_regras()
    assert [(x["slug"], x["status"], x["dias"]) for x in lista] == [
        ("vencida", "vencida", -2), ("em-dia", "em_dia", 1), ("fragil", "fragil", 3), ("sem-agenda", "em_dia", None)]
    assert lista[0]["explicacao_md"] == "texto vencida"


# ------------------------------------------------------------------ esquema 4

def test_esquema_4_refaz_exercicio_sem_perder_respostas(tmp_path):
    caminho = tmp_path / "v3.db"
    raw = sqlite3.connect(caminho)
    raw.executescript(db._DDL.read_text() + db._DDL2.read_text() + db._DDL3.read_text())
    raw.execute("PRAGMA user_version = 3")
    raw.execute("INSERT INTO licao (id, data, titulo) VALUES (1, '2026-10-22', 'antiga')")
    raw.execute("INSERT INTO exercicio (id, licao_id, ordem, bloco, tipo, enunciado, dados) "
                "VALUES (7, 1, 1, 'verificacao', 'ouvir', 'x', '{\"texto\": \"a\"}')")
    raw.execute("INSERT INTO resposta (exercicio_id, resposta, veredito) VALUES (7, '{\"texto\": \"a\"}', 'certo')")
    raw.commit()
    raw.close()

    c = db.conectar(caminho)
    assert c.execute("PRAGMA user_version").fetchone()[0] == db.ESQUEMA_ATUAL >= 4    # e segue até o atual
    assert c.execute("SELECT COUNT(*) FROM resposta WHERE exercicio_id = 7").fetchone()[0] == 1
    assert c.execute("SELECT regra_id FROM exercicio WHERE id = 7").fetchone()[0] is None
    assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    c.execute("INSERT INTO regra (slug, titulo) VALUES ('a', 'A')")
    c.execute("INSERT INTO exercicio (licao_id, ordem, bloco, tipo, enunciado, dados, regra_id) "
              "VALUES (1, 2, 'novo', 'explicacao', '', '{\"md\": \"x\"}', 1)")     # o CHECK novo aceita
    c.execute("DELETE FROM licao WHERE id = 1")                         # e a cascata segue valendo
    assert c.execute("SELECT COUNT(*) FROM resposta").fetchone()[0] == 0
    c.close()
