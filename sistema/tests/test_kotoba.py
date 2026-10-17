"""Testes do leitor do Kotoba (japones/fontes/kotoba.py).

Rodam contra os bancos DE VERDADE deste PC (o dicionário instalado e o user.db
dele), porque o que importa conferir é o contrato com o app — e que a leitura
nunca encosta nos arquivos. Sem o Kotoba instalado, os testes que precisam dos
bancos são PULADOS, não falham.

    pytest sistema/tests/test_kotoba.py
    python3 sistema/tests/test_kotoba.py      (sem pytest: roda tudo e resume)
"""
import os
import sys
import tempfile
import traceback
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # sistema/

from japones.fontes import kotoba  # noqa: E402

try:
    import pytest
except ImportError:  # sem pytest: o __main__ abaixo faz as vezes dele
    pytest = None

_MODO_SCRIPT = False


class _Pulado(Exception):
    pass


def _pular(motivo):
    if pytest is not None and not _MODO_SCRIPT:
        pytest.skip(motivo)
    raise _Pulado(motivo)


def _exige_dicionario():
    try:
        return kotoba.caminho_dicionario()
    except kotoba.KotobaIndisponivel as e:
        _pular(str(e))


def _exige_user_db():
    try:
        return kotoba.caminho_user_db()
    except kotoba.KotobaIndisponivel as e:
        _pular(str(e))


def _hira(s):
    """Katakana → hiragana (o KANJIDIC2 guarda on'yomi em katakana)."""
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def _assinatura(caminho):
    """mtime (ns) e tamanho do arquivo e dos -wal/-shm, se existirem."""
    saida = {}
    for sufixo in ("", "-wal", "-shm"):
        p = Path(str(caminho) + sufixo)
        if p.exists():
            st = p.stat()
            saida[sufixo] = (st.st_mtime_ns, st.st_size)
    return saida


# ------------------------------------------------------------------ sem banco


def test_normalizacao_japonesa():
    assert kotoba.norm_ja("ｺｰﾋｰ") == "こおひい"
    assert kotoba.norm_ja("コーヒー") == "こおひい"
    assert kotoba.norm_ja("ＣＤプレーヤー") == "cdぷれえやあ"
    assert kotoba.norm_ja("ヴァイオリン") == "ゔぁいおりん"
    assert kotoba.norm_ja("食べる") == "食べる"


def test_dobra_e_tokens_latinos():
    assert kotoba.fold("Coração") == "coracao"
    assert kotoba.query_tokens("Sentar-se") == ["sentar", "se"]
    assert kotoba.ntok_of("sentar-se", "pt") == 1
    assert kotoba.ntok_of("dar-lhe", "pt") == 1
    assert kotoba.ntok_of("semana passada", "pt") == 2


def test_variantes_pt_seguem_o_app():
    # Exemplos de DESIGN §6.4.1 / pt_variants.dart
    def v(w):
        return [" ".join(t) for t, _ in kotoba.variantes_pt([w])]

    assert v("casas") == ["casas", "casa", "caso"]
    assert v("taxis") == ["taxis", "taxi", "taxil"]
    assert v("maes") == ["maes", "mae"]
    assert v("porta") == ["porta", "porto"]
    assert v("mais") == ["mais"]
    assert v("reis") == ["reis", "rei"]
    assert v("ares") == ["ares", "ar", "are"]
    pen = dict((" ".join(t), p) for t, p in kotoba.variantes_pt(["valores"]))
    assert pen == {"valores": 0, "valor": 1000, "valore": 1000}


def test_sem_kotoba_levanta_indisponivel():
    antes = os.environ.get("JAPONES_KOTOBA")
    with tempfile.TemporaryDirectory() as vazio:
        os.environ["JAPONES_KOTOBA"] = vazio
        try:
            for funcao in (kotoba.caminho_dicionario, kotoba.caminho_user_db, kotoba.historico):
                try:
                    funcao()
                except kotoba.KotobaIndisponivel as e:
                    assert str(e)  # mensagem em português para quem degrada
                else:
                    raise AssertionError(f"{funcao.__name__} não levantou KotobaIndisponivel")
        finally:
            if antes is None:
                os.environ.pop("JAPONES_KOTOBA", None)
            else:
                os.environ["JAPONES_KOTOBA"] = antes


# ------------------------------------------------------------------ dicionário


def test_motsu_leitura_e_glosa():
    _exige_dicionario()
    r = kotoba.buscar("持つ")
    assert r, "持つ não encontrado"
    m = r[0]
    assert m["palavra"] == "持つ"
    assert m["leitura"] == "もつ"
    assert any("segurar" in g for g in m["glosas_pt"]), m["glosas_pt"]
    assert m["jlpt"] == 5 and m["comum"] is True
    assert "v5t" in m["classe"]
    assert m["url"] == f"kotoba://palavra/{m['ent_seq']}"
    assert m["casamento"] == "exato"
    assert "sentidos" not in m  # enxuto por padrão
    d = kotoba.buscar("持つ", 1, detalhado=True)[0]
    assert d["sentidos"][0]["classe"] == m["classe"]
    assert any("segurar" in g for g in d["sentidos"][0]["pt"])


def test_kana_acha_kau():
    _exige_dicionario()
    assert "買う" in [x["palavra"] for x in kotoba.buscar("かう")]
    # katakana e largura cheia/meia caem na mesma chave (§5.4.1)
    assert "買う" in [x["palavra"] for x in kotoba.buscar("カウ")]


def test_portugues_acha_kau():
    _exige_dicionario()
    r = kotoba.buscar("comprar")
    assert "買う" in [x["palavra"] for x in r]
    kau = next(x for x in r if x["palavra"] == "買う")
    assert kau["casamento"] == "pt" and "comprar" in kau["glosas_pt"]


def test_toru_de_fotografia():
    _exige_dicionario()
    r = kotoba.buscar("撮る")
    assert r and r[0]["palavra"] == "撮る" and r[0]["leitura"] == "とる"


def test_usual_em_kana_vira_titulo():
    _exige_dicionario()
    r = kotoba.buscar("ｺｰﾋｰ")
    assert r and r[0]["palavra"] == "コーヒー" and r[0]["grafia_kanji"] == "珈琲"


def test_vazio_e_uma_letra_nao_buscam():
    _exige_dicionario()
    assert kotoba.buscar("") == []
    assert kotoba.buscar("   ") == []
    assert kotoba.buscar("a") == []


def test_kanji_shoku():
    _exige_dicionario()
    k = kotoba.kanji("食")
    assert k is not None
    assert "しょく" in [_hira(x) for x in k["on"]], k["on"]
    assert k["tracos"] == 9 and k["jlpt"] == 5
    assert any("comer" in s for s in k["significados_pt"])
    assert k["url"] == "kotoba://kanji/食"
    assert kotoba.kanji("ab") is None and kotoba.kanji("a") is None


def test_dicionario_nao_e_alterado():
    caminho = _exige_dicionario()
    pasta_antes = sorted(p.name for p in caminho.parent.iterdir())
    antes = _assinatura(caminho)
    kotoba.buscar("持つ")
    kotoba.buscar("comprar")
    kotoba.kanji("食")
    assert _assinatura(caminho) == antes
    assert sorted(p.name for p in caminho.parent.iterdir()) == pasta_antes


# ------------------------------------------------------------------ user.db


def test_historico_formato():
    _exige_user_db()
    h = kotoba.historico(limite=50)  # não pode levantar, nem com o app aberto gravando
    assert isinstance(h, list)
    for item in h:
        assert item["tipo"] in ("query", "entry", "kanji")
        quando = datetime.fromisoformat(item["quando"])  # ISO-8601 válido
        assert quando.tzinfo is None  # hora local ingênua, como desde/ate
        assert isinstance(item["rotulo"], str)
        if item["tipo"] == "entry":
            assert isinstance(item["ent_seq"], int)
    ms = [item["quando_ms"] for item in h]
    assert ms == sorted(ms, reverse=True), "histórico fora de ordem (mais recente primeiro)"


def test_historico_intervalo():
    _exige_user_db()
    h = kotoba.historico(limite=1000)
    if len(h) < 2:
        _pular("histórico com menos de 2 linhas")
    corte = datetime.fromtimestamp(h[len(h) // 2]["quando_ms"] / 1000)
    depois = kotoba.historico(desde=corte, limite=1000)
    antes = kotoba.historico(ate=corte, limite=1000)
    assert all(i["quando_ms"] >= h[len(h) // 2]["quando_ms"] for i in depois)
    assert all(i["quando_ms"] < h[len(h) // 2]["quando_ms"] for i in antes)
    assert len(depois) + len(antes) == len(h)  # meio-aberto: nenhuma linha em dobro
    assert kotoba.historico(desde=datetime.now() + timedelta(days=1)) == []


def test_user_db_nao_e_alterado():
    caminho = _exige_user_db()
    pasta_antes = sorted(p.name for p in caminho.parent.iterdir())
    antes = _assinatura(caminho)
    kotoba.historico()
    kotoba.listas()
    # Se o app estiver aberto e gravar exatamente agora, isto acusa falso positivo:
    # rode de novo. O que nunca pode acontecer é aparecer arquivo novo ao lado.
    assert _assinatura(caminho) == antes
    assert sorted(p.name for p in caminho.parent.iterdir()) == pasta_antes


def test_copias_temporarias_sao_apagadas():
    _exige_user_db()
    tmp = Path(tempfile.gettempdir())
    antes = set(tmp.glob("kotoba-user-*"))
    kotoba.historico(limite=5)
    kotoba.listas()
    assert set(tmp.glob("kotoba-user-*")) == antes


def test_listas_tem_favoritos():
    _exige_user_db()
    ls = kotoba.listas()
    assert any(l["favoritos"] for l in ls)  # o app cria "Favoritos" na migração
    for l in ls:
        assert l["total"] == len(l["itens"])


# ------------------------------------------------------------------ sem pytest


if __name__ == "__main__":
    _MODO_SCRIPT = True
    testes = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    ok, pulados, falhas = 0, [], []
    for nome, teste in testes:
        try:
            teste()
        except _Pulado as e:
            pulados.append((nome, str(e)))
            print(f"PULOU  {nome}: {e}")
        except Exception:
            falhas.append(nome)
            print(f"FALHOU {nome}")
            traceback.print_exc()
        else:
            ok += 1
            print(f"ok     {nome}")
    print(f"\n{ok} passaram, {len(falhas)} falharam, {len(pulados)} pulados (de {len(testes)})")
    sys.exit(1 if falhas else 0)
