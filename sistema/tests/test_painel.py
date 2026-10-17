"""Telas da Fase 3 (DESIGN §12): agregados de erros, Anki com fallback e Kotoba × Anki.
Anki e Kotoba são trocados por funções falsas: nada aqui lê os apps de verdade."""
from datetime import timedelta

import pytest

from japones import config, db, dominio, exercicios as m, painel
from japones.exercicios import ExercicioIn as E


@pytest.fixture
def con():
    if config.BANCO.exists():
        config.BANCO.unlink()
    c = db.conectar()
    yield c
    c.close()


def _dia(n: int) -> str:
    return (dominio.dia_de_estudo() - timedelta(days=n)).isoformat()


def test_erros_por_grupo_e_por_semana(con):
    hoje = dominio.dia_de_estudo()
    segunda = hoje - timedelta(days=hoje.weekday())
    for data, cat in [(segunda, "particula:wo"), (segunda, "particula:ni-de"), (segunda, "forma-te"),
                      (segunda - timedelta(days=7), "particula:wo"), (hoje - timedelta(days=200), "particula:wo")]:
        con.execute("INSERT INTO erro (data, bloco, categoria) VALUES (?, 'producao', ?)", (data.isoformat(), cat))
    con.commit()
    r = painel.erros_painel(con, dias=90)
    assert r["total"] == 4                                   # o de 200 dias atrás fica fora
    assert r["por_categoria"][0] == {"categoria": "particula:wo", "grupo": "particula", "n": 2,
                                     "ultimo": segunda.isoformat()}
    assert {"semana": segunda.isoformat(), "grupo": "particula", "n": 2} in r["por_semana"]
    assert {"semana": (segunda - timedelta(days=7)).isoformat(), "grupo": "particula", "n": 1} in r["por_semana"]
    assert r["por_bloco"] == {"producao": 4}


def test_acerto_por_tipo_conta_so_a_primeira_resposta(con):
    lid = m.criar_licao(con, "t", [E(tipo="escolha", enunciado="x", dados={"opcoes": ["a", "b"], "correta": "a"}),
                                   E(tipo="producao", bloco="producao", enunciado="y", dados={})], _dia(0))
    exs = m.licao_renderizada(con, lid)["exercicios"]
    m.responder(con, exs[0]["id"], {"opcao": "b"})
    m.responder(con, exs[0]["id"], {"opcao": "a"})          # a segunda não conta
    m.responder(con, exs[1]["id"], {"frases": ["…"]})
    tipos = {t["tipo"]: t for t in painel.erros_painel(con)["tipos_exercicio"]}
    assert tipos["escolha"] == {"tipo": "escolha", "respondidos": 1, "certos": 0, "errados": 1, "revisar": 0,
                                "taxa_erro": 1.0}
    assert tipos["producao"]["revisar"] == 1 and tipos["producao"]["taxa_erro"] is None


def test_anki_fora_do_ar_cai_no_trajeto_gravado(con, monkeypatch):
    from japones.fontes import anki

    def caiu(*a, **k):
        raise anki.AnkiIndisponivel("coleção não encontrada")
    for f in ("status", "graficos", "historico_por_dia"):
        monkeypatch.setattr(anki, f, caiu)
    con.execute("INSERT INTO trajeto (data, anki_cartoes, anki_minutos, audio) VALUES (?, 120, 30.5, 1)",
                (config.INICIO_PLANO.isoformat(),))
    con.commit()
    r = painel.anki_painel(con)
    assert "erro" in r["status"] and "erro" in r["graficos"] and "fonte_por_dia" in r
    assert r["por_dia"][0] == {"data": config.INICIO_PLANO.isoformat(), "cartoes": 120, "minutos": 30.5, "audio": 1}
    assert r["por_dia"][-1]["data"] == dominio.dia_de_estudo().isoformat()     # todo dia, até hoje, sem buraco
    assert r["por_dia"][1]["audio"] is None                                      # não informado ≠ não ouviu


def test_kotoba_sem_cartao_e_dia_de_estudo(monkeypatch):
    from japones.fontes import anki, kotoba
    hoje = dominio.dia_de_estudo()
    madrugada = f"{(hoje + timedelta(days=1)).isoformat()}T02:18:37"        # 02:18 do dia seguinte = hoje
    consultas = [
        {"tipo": "entry", "rotulo": "持つ · segurar", "consulta": None, "kanji": None, "quando": madrugada, "ent_seq": 1},
        {"tipo": "entry", "rotulo": "買う · comprar", "consulta": None, "kanji": None, "quando": madrugada, "ent_seq": 2},
        {"tipo": "entry", "rotulo": "持つ · segurar", "consulta": None, "kanji": None,
         "quando": f"{hoje.isoformat()}T21:00:00", "ent_seq": 1},
        {"tipo": "query", "rotulo": "ter", "consulta": "ter", "kanji": None, "quando": madrugada, "ent_seq": None},
    ]
    monkeypatch.setattr(kotoba, "historico", lambda **k: consultas)
    monkeypatch.setattr(kotoba, "buscar", lambda termo, limite=5, **k: [
        {"ent_seq": 1, "leitura": "もつ"}, {"ent_seq": 2, "leitura": "かう"}])
    monkeypatch.setattr(anki, "indice_de_cartoes", lambda: {"campos": {"かう", "もつ", "comprar"},
                                                            "frentes_kana": {"かう"}})
    # 買う tem cartão pela leitura (frente em kana); 持つ não: もつ é só um campo, pode ser de um homófono
    r = painel.kotoba_historico(dias=7)
    assert [d["data"] for d in r["dias"]] == [hoje.isoformat()]
    assert r["sem_cartao"] == [{"palavra": "持つ", "leitura": "もつ", "rotulo": "持つ · segurar", "vezes": 2,
                                "ultima": hoje.isoformat()}]
    tem = {c["rotulo"]: c.get("tem_cartao") for c in r["dias"][0]["consultas"]}
    assert tem == {"持つ · segurar": False, "買う · comprar": True, "ter": None}


def test_kotoba_com_anki_fechado_nao_chuta(monkeypatch):
    from japones.fontes import anki, kotoba
    monkeypatch.setattr(kotoba, "historico", lambda **k: [
        {"tipo": "entry", "rotulo": "持つ · segurar", "consulta": None, "kanji": None,
         "quando": f"{dominio.dia_de_estudo().isoformat()}T21:00:00", "ent_seq": 1}])
    monkeypatch.setattr(kotoba, "buscar", lambda *a, **k: [])

    def caiu():
        raise anki.AnkiIndisponivel("fechado")
    monkeypatch.setattr(anki, "indice_de_cartoes", caiu)
    r = painel.kotoba_historico(dias=1)
    assert r["dias"][0]["consultas"][0]["tem_cartao"] is None and r["sem_cartao"] == [] and "aviso" in r


def test_homofono_nao_herda_o_cartao(monkeypatch):
    """押す tem cartão no Kaishi (campos 押す e おす); お酢, também おす, não tem."""
    from japones.fontes import anki, kotoba
    monkeypatch.setattr(kotoba, "buscar", lambda *a, **k: [
        {"palavra": "押す", "grafia_kanji": "押す", "leitura": "おす"},
        {"palavra": "お酢", "grafia_kanji": "お酢", "leitura": "おす"},
        {"palavra": "海", "grafia_kanji": "海", "leitura": "うみ"}])
    monkeypatch.setattr(anki, "indice_de_cartoes", lambda: {"campos": {"押す", "おす", "うみ"}, "frentes_kana": {"うみ"}})
    r = painel.kotoba_buscar("おす")
    assert [x["tem_cartao"] for x in r["resultados"]] == [True, False, True]
