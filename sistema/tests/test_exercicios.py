"""Motor de exercícios (DESIGN §9): validação, render sem gabarito, correção, erro automático e sorteio."""
import json

import pytest

from japones import config, db, exercicios as m
from japones.exercicios import ExercicioIn as E


@pytest.fixture
def con():
    for p in (config.BANCO,):
        if p.exists():
            p.unlink()
    c = db.conectar()
    yield c
    c.close()


UM_DE_CADA = [
    E(tipo="escolha", bloco="aquecimento", enunciado="Qual partícula? 猫＿部屋にいます", categoria="particula:wa-ga",
      dados={"opcoes": ["は", "に", "で", "を"], "correta": "は"}, explicacao="quem existe leva は/が"),
    E(tipo="achar_erro", enunciado="Ache o erro", categoria="particula:wo",
      dados={"segmentos": ["日本を", "行ったことが", "ありません"], "errado": 0, "correcao": "日本に"}),
    E(tipo="ligar", enunciado="Ligue o verbo à forma て",
      dados={"pares": [["書く", "書いて"], ["飲む", "飲んで"], ["撮る", "撮って"]]}),
    E(tipo="ordenar", enunciado="Monte: o gato está no quarto", categoria="particula:posicao",
      dados={"pecas": ["猫は", "部屋に", "います"], "aceitas": [["猫は", "部屋に", "います"], ["部屋に", "猫は", "います"]],
             "distratores": ["で"]}),
    E(tipo="completar", enunciado="Complete", categoria="particula:ni-de",
      dados={"texto": "猫{0}部屋{1}います", "lacunas": [{"aceitas": ["は", "が"], "opcoes": ["は", "が", "に", "で"]},
                                                       {"aceitas": ["に"]}]}),
    E(tipo="digitar", enunciado="Nunca fui ao Japão.", categoria="forma-ta",
      dados={"aceitas": ["日本に行ったことがありません", "にほんにいったことがありません"]}),
    E(tipo="conjugar", enunciado="Forma て", categoria="forma-te",
      dados={"verbo": "撮る", "leitura": "とる", "forma": "forma て", "aceitas": ["撮って", "とって"]}),
    E(tipo="producao", bloco="producao", enunciado="3 frases com 〜たことがあります", dados={"minimo": 3}),
]


def test_render_nunca_leva_o_gabarito(con):
    lid = m.criar_licao(con, "teste", UM_DE_CADA, "2026-10-17")
    l = m.licao_renderizada(con, lid)
    texto = json.dumps(l, ensure_ascii=False)
    for proibido in ('"correta"', '"aceitas"', '"errado"', '"correcao"', '"pares"'):
        assert proibido not in texto
    assert [e["tipo"] for e in l["exercicios"]] == [e.tipo for e in UM_DE_CADA]


def test_render_e_estavel_e_embaralha_o_ordenar(con):
    lid = m.criar_licao(con, "teste", UM_DE_CADA, "2026-10-17")
    a, b = m.licao_renderizada(con, lid), m.licao_renderizada(con, lid)
    assert a == b                                  # recarregar não troca a ordem
    pecas = a["exercicios"][3]["render"]["pecas"]
    assert sorted(pecas) == sorted(["猫は", "部屋に", "います", "で"])
    assert pecas[:3] not in (["猫は", "部屋に", "います"], ["部屋に", "猫は", "います"])


def test_validacao_recusa_a_licao_inteira(con):
    ruim = E(tipo="escolha", enunciado="x", dados={"opcoes": ["a", "b"], "correta": "c"})
    with pytest.raises(ValueError, match="exercício 2"):
        m.criar_licao(con, "teste", [UM_DE_CADA[0], ruim])
    assert con.execute("SELECT COUNT(*) FROM licao").fetchone()[0] == 0


@pytest.mark.parametrize("tipo,dados,resp,esperado", [
    ("escolha", {"opcoes": ["は", "に"], "correta": "は"}, {"opcao": "は"}, "certo"),
    ("escolha", {"opcoes": ["は", "に"], "correta": "は"}, {"opcao": "に"}, "errado"),
    ("achar_erro", {"segmentos": ["a", "b"], "errado": 1, "correcao": "c"}, {"segmento": 1}, "certo"),
    ("ligar", {"pares": [["a", "1"], ["b", "2"], ["c", "3"]]}, {"pares": [["a", "1"], ["b", "2"], ["c", "3"]]}, "certo"),
    ("ligar", {"pares": [["a", "1"], ["b", "2"], ["c", "3"]]}, {"pares": [["a", "2"], ["b", "1"], ["c", "3"]]}, "errado"),
    ("ordenar", {"pecas": ["猫は", "部屋に", "います"], "aceitas": [["猫は", "部屋に", "います"], ["部屋に", "猫は", "います"]]},
     {"pecas": ["部屋に", "猫は", "います"]}, "certo"),
    ("ordenar", {"pecas": ["猫は", "部屋に", "います"]}, {"pecas": ["部屋に", "います", "猫は"]}, "errado"),
    ("completar", {"texto": "猫{0}部屋{1}います", "lacunas": [{"aceitas": ["は", "が"]}, {"aceitas": ["に"]}]},
     {"lacunas": ["が", "に"]}, "certo"),
    ("completar", {"texto": "猫{0}部屋{1}います", "lacunas": [{"aceitas": ["は", "が"]}, {"aceitas": ["に"]}]},
     {"lacunas": ["は", "で"]}, "errado"),
    ("digitar", {"aceitas": ["日本に行ったことがありません"]}, {"texto": "日本に 行ったことがありません。"}, "certo"),
    ("digitar", {"aceitas": ["日本に行ったことがありません"]}, {"texto": "日本を行ったことがありません"}, "revisar"),
    ("conjugar", {"verbo": "撮る", "forma": "て", "aceitas": ["撮って", "とって"]}, {"texto": "とって"}, "certo"),
    ("conjugar", {"verbo": "撮る", "forma": "て", "aceitas": ["撮って", "とって"]}, {"texto": "とりて"}, "errado"),
    ("producao", {"minimo": 1}, {"frases": ["すしを食べたことがあります"]}, "revisar"),
])
def test_correcao_por_tipo(tipo, dados, resp, esperado):
    assert m.corrigir(tipo, dados, resp)[0] == esperado


def test_katakana_e_hiragana_nao_se_equivalem():
    assert m.corrigir("digitar", {"aceitas": ["ペン"]}, {"texto": "ぺん"})[0] == "revisar"


def test_diff_mostra_o_que_faltou_e_o_que_sobrou():
    ops = m.diff("のんて", "のんで")
    assert {"op": "sobrou", "texto": "て"} in ops and {"op": "faltou", "texto": "で"} in ops


def test_primeiro_erro_vai_para_a_tabela_erro_e_so_ele_conta(con):
    lid = m.criar_licao(con, "teste", UM_DE_CADA, "2026-10-17")
    ex = m.licao_renderizada(con, lid)["exercicios"][0]           # escolha, categoria particula:wa-ga
    r1 = m.responder(con, ex["id"], {"opcao": "に"}, 3000)
    r2 = m.responder(con, ex["id"], {"opcao": "は"}, 1000)
    assert (r1["veredito"], r1["contou"], r2["veredito"], r2["contou"]) == ("errado", True, "certo", False)
    erros = con.execute("SELECT data, bloco, categoria, escrito, correto FROM erro").fetchall()
    assert [tuple(e) for e in erros] == [("2026-10-17", "abertura", "particula:wa-ga", "に", "は")]
    assert m.licao_renderizada(con, lid)["exercicios"][0]["resultado"]["veredito"] == "errado"


def test_tutor_fecha_o_revisar_e_a_licao_conclui(con):
    lid = m.criar_licao(con, "teste", [UM_DE_CADA[0], UM_DE_CADA[7]], "2026-10-17")
    exs = m.licao_renderizada(con, lid)["exercicios"]
    m.responder(con, exs[0]["id"], {"opcao": "は"})
    assert m.resumo_licoes(con)[0]["status"] == "aberta"
    m.responder(con, exs[1]["id"], {"frases": ["日本を行ったことがあります"]})
    assert m.resumo_licoes(con)[0]["status"] == "concluida"
    assert m.corrigir_revisao(con, exs[1]["id"], "errado", "↪️ 日本**に**行ったことがあります")
    res = m.licao_renderizada(con, lid)["exercicios"][1]["resultado"]
    assert res["veredito"] == "errado" and "日本**に**" in res["correcao"]
    assert con.execute("SELECT COUNT(*) FROM erro WHERE bloco = 'producao'").fetchone()[0] == 1


def test_sorteio_usa_todos_e_termina_em_producao(con):
    p = m.planejar_tipos(con, n=8, semente=1)
    assert sorted(p["tipos"]) == sorted(m.TIPOS) and p["tipos"][-1] == "producao"
    p = m.planejar_tipos(con, n=5, semente=2)
    assert len(p["tipos"]) == 5 and p["tipos"][-1] == "producao"
    assert max(p["tipos"].count(t) for t in m.TIPOS) <= 2


def test_sorteio_favorece_o_tipo_que_ele_erra(con):
    lid = m.criar_licao(con, "erra conjugar", [UM_DE_CADA[6]] * 3 + [UM_DE_CADA[0]] * 3)
    for ex in m.licao_renderizada(con, lid)["exercicios"]:
        resp = {"texto": "とりて"} if ex["tipo"] == "conjugar" else {"opcao": "は"}
        m.responder(con, ex["id"], resp)
    pesos = m.planejar_tipos(con, n=8, semente=3)["pesos"]
    assert pesos["conjugar"] > pesos["escolha"]
