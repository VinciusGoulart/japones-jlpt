"""O Anki em dados (o tools/anki_status.py imprime; este devolve dicionários).

SÓ LÊ, e de uma CÓPIA: a localização e a cópia da coleção vêm do próprio
anki_status.py (achar_fonte copia o arquivo e o -wal antes de abrir), para que
existam um jeito só de achar a coleção e um jeito só de errar.
"""
import importlib.util
import re
import shutil
import sqlite3
import time
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

from japones import config


class AnkiIndisponivel(Exception):
    pass


def _ferramenta():
    spec = importlib.util.spec_from_file_location("anki_status", config.TOOLS / "anki_status.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@contextmanager
def colecao():
    """Abre uma cópia da coleção; a cópia é apagada na saída."""
    tool = _ferramenta()
    try:
        caminho, rotulo, mtime, origem = tool.achar_fonte(None)
        db = caminho if caminho.endswith(".anki2") else tool.abrir(caminho)
    except SystemExit as e:      # a ferramenta encerra o processo quando não acha nada
        raise AnkiIndisponivel("coleção do Anki não encontrada (nem desktop, nem export)") from e
    con = sqlite3.connect(db) if origem == "desktop" else sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        yield con, tool, {"fonte": origem, "rotulo": rotulo,
                          "idade_dias": round((time.time() - mtime) / 86400, 2)}
    finally:
        con.close()
        if origem == "desktop":
            shutil.rmtree(Path(db).parent, ignore_errors=True)


def _frente(flds: str) -> str:
    return flds.split("\x1f")[0][:60]


#: cor da bandeira (cards.flags & 7). Desde 25/10 duas têm combinado com ele: ROXA = "não consigo
#: assimilar o sentido e a fala" (vai para a análise na mesa) e LARANJA = "o trocadilho falta ou está
#: ruim" (o tutor reescreve e tira a bandeira).
CORES = {1: "vermelha", 2: "laranja", 3: "verde", 4: "azul", 5: "rosa", 6: "turquesa", 7: "roxa"}


def status() -> dict:
    with colecao() as (con, tool, fonte):
        (crt,) = con.execute("SELECT crt FROM col").fetchone()
        hoje = tool.dia_anki(crt)
        decks = tool.nomes_de_deck(con)

        baralhos = [
            {"baralho": decks.get(did, f"?{did}"), "total": tot, "novos": novos or 0,
             "devidos": dev or 0, "aprendendo": apr or 0, "suspensos": susp or 0}
            for did, tot, novos, dev, apr, susp in con.execute("""
                SELECT did, COUNT(*), SUM(queue = 0), SUM(queue = 2 AND due <= ?),
                       SUM(queue IN (1, 3)), SUM(queue = -1)
                FROM cards GROUP BY did ORDER BY COUNT(*) DESC""", (hoje,))
        ]
        (atrasados,) = con.execute(
            "SELECT COUNT(*) FROM cards WHERE queue = 2 AND due < ?", (hoje,)).fetchone()

        dias = []
        for d in range(6, -1, -1):
            ini, fim = tool.inicio_do_dia_ms(d), tool.inicio_do_dia_ms(d - 1)
            n, ms = con.execute("SELECT COUNT(*), COALESCE(SUM(time), 0) FROM revlog "
                                "WHERE id >= ? AND id < ?", (ini, fim)).fetchone()
            dias.append({"dias_atras": d, "cartoes": n, "minutos": round(ms / 60000)})

        ini30 = tool.inicio_do_dia_ms(30)
        tot, ok = con.execute("SELECT COUNT(*), SUM(ease > 1) FROM revlog "
                              "WHERE id >= ? AND type = 1", (ini30,)).fetchone()
        botoes = dict(con.execute("SELECT ease, COUNT(*) FROM revlog WHERE id >= ? AND type = 1 "
                                  "GROUP BY ease", (ini30,)).fetchall())
        tot_b = sum(botoes.values()) or 1

        travam = [{"frente": _frente(f), "lapses": l, "baralho": decks.get(did, "")}
                  for f, l, did in con.execute("""
                      SELECT n.flds, c.lapses, c.did FROM cards c JOIN notes n ON n.id = c.nid
                      WHERE c.lapses >= 3 ORDER BY c.lapses DESC LIMIT 12""")]
        loop = [{"frente": _frente(f), "again_7d": a, "baralho": decks.get(did, "")}
                for f, a, did in con.execute("""
                    SELECT n.flds, COUNT(*) AS agains, c.did FROM revlog r
                    JOIN cards c ON c.id = r.cid JOIN notes n ON n.id = c.nid
                    WHERE r.id >= ? AND r.ease = 1
                    GROUP BY r.cid HAVING agains >= 3 ORDER BY agains DESC LIMIT 15""",
                    (tool.inicio_do_dia_ms(6),))]
        bandeira = [{"frente": _frente(f), "baralho": decks.get(did, ""), "cor": CORES[fl & 7]}
                    for f, did, fl in con.execute("""
                        SELECT n.flds, c.did, c.flags FROM cards c JOIN notes n ON n.id = c.nid
                        WHERE c.flags & 7 != 0 ORDER BY (c.flags & 7) = 7 DESC, c.mod DESC LIMIT 30""")]

    retencao = round(ok / tot * 100, 1) if tot else None
    return {
        "fonte": fonte,
        "baralhos": baralhos,
        "fila_atrasados": atrasados,
        "alerta_fila": "zerar novos" if atrasados > 200 else ("não subir novos" if atrasados > 100 else None),
        "ultimos_7_dias": dias,
        "retencao_30d": retencao,
        "alerta_retencao": ("abaixo de 85%: reduzir novos" if retencao is not None and retencao < 85
                            else "acima de 95%: dá para subir novos" if retencao and retencao > 95 else None),
        "botoes_30d_pct": {nome: round(botoes.get(e, 0) / tot_b * 100)
                           for e, nome in ((1, "again"), (2, "hard"), (3, "good"), (4, "easy"))},
        "travam": travam,
        "em_loop": loop,
        "bandeira": bandeira,
    }


def historico_por_dia(desde: date = config.INICIO_PLANO) -> list[dict]:
    """Cartões e minutos por DIA DE ESTUDO (vira às 04:00), para o trajeto."""
    with colecao() as (con, _tool, _fonte):
        rows = con.execute(f"""
            SELECT date(id / 1000, 'unixepoch', 'localtime', '-{config.ROLLOVER_H} hours') AS dia,
                   COUNT(*), SUM(time)
            FROM revlog GROUP BY dia HAVING dia >= ? ORDER BY dia""", (desde.isoformat(),)).fetchall()
    return [{"data": d, "cartoes": n, "minutos": round((ms or 0) / 60000, 1)} for d, n, ms in rows]


def graficos(dias_previsao: int = 14, semanas: int = 12) -> dict:
    """Os gráficos da tela Anki (DESIGN §12.2): retenção por semana, maturidade e previsão."""
    from japones import dominio
    with colecao() as (con, tool, _fonte):
        (crt,) = con.execute("SELECT crt FROM col").fetchone()
        hoje = tool.dia_anki(crt)
        por_dia = con.execute(f"""
            SELECT date(id / 1000, 'unixepoch', 'localtime', '-{config.ROLLOVER_H} hours') AS dia,
                   COUNT(*), SUM(ease > 1)
            FROM revlog WHERE type = 1 GROUP BY dia HAVING dia >= ?""", (config.INICIO_PLANO.isoformat(),)).fetchall()
        (novos, aprendendo, jovens, maduros, suspensos) = con.execute("""
            SELECT SUM(queue = 0), SUM(queue IN (1, 3)), SUM(queue = 2 AND ivl < 21),
                   SUM(queue = 2 AND ivl >= 21), SUM(queue < 0) FROM cards""").fetchone()
        devidos = dict(con.execute("SELECT due, COUNT(*) FROM cards WHERE queue IN (2, 3) AND due < ? GROUP BY due",
                                   (hoje + dias_previsao,)).fetchall())
        (aprendendo_hoje,) = con.execute("SELECT COUNT(*) FROM cards WHERE queue = 1").fetchone()

    semanal: dict[str, list[int]] = {}
    for dia, n, ok in por_dia:
        d = date.fromisoformat(dia)
        seg = (d - timedelta(days=d.weekday())).isoformat()
        acc = semanal.setdefault(seg, [0, 0])
        acc[0] += n
        acc[1] += ok or 0
    retencao = [{"semana": s, "revisoes": n, "acertos": ok, "pct": round(ok / n * 100, 1)}
                for s, (n, ok) in sorted(semanal.items())[-semanas:]]

    dia0 = dominio.dia_de_estudo()
    previsao = []
    for i in range(dias_previsao):
        n = devidos.get(hoje + i, 0)
        if i == 0:      # o dia de hoje carrega os atrasados e o que está em aprendizado agora
            n = sum(v for k, v in devidos.items() if k <= hoje) + aprendendo_hoje
        previsao.append({"data": (dia0 + timedelta(days=i)).isoformat(), "devidos": n})
    return {"retencao_semanal": retencao,
            "maturidade": {"novos": novos or 0, "aprendendo": aprendendo or 0, "jovens": jovens or 0,
                           "maduros": maduros or 0, "suspensos": suspensos or 0},
            "previsao": previsao}


_TAG = re.compile(r"<[^>]+>|\[sound:[^\]]*\]|&nbsp;")


_KANA = re.compile(r"^[\u3040-\u30ffー]+$")


def indice_de_cartoes() -> dict[str, set[str]]:
    """Para saber se uma palavra do Kotoba já virou cartão (DESIGN §12.4).

    `campos`: todo campo de toda nota, sem HTML. Campo INTEIRO, não trecho — 食べ
    dentro de uma frase de exemplo não é um cartão de 食べる.
    `frentes_kana`: a frente (1º campo) das notas escritas só em kana (うみ, はし).
    A leitura de uma palavra só casa por aqui: no Kaishi a leitura おす é campo da
    nota de 押す, e casar leitura com qualquer campo marcava お酢 e 雄 como "tem
    cartão" (achado no teste da tela Kotoba, 17/10).
    """
    with colecao() as (con, _tool, _fonte):
        campos, frentes_kana = set(), set()
        for (flds,) in con.execute("SELECT flds FROM notes"):
            limpos = [_TAG.sub("", f).strip() for f in flds.split("\x1f")]
            campos.update(f for f in limpos if f)
            if limpos and _KANA.match(limpos[0]):
                frentes_kana.add(limpos[0])
    return {"campos": campos, "frentes_kana": frentes_kana}
