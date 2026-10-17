"""O Anki em dados (o tools/anki_status.py imprime; este devolve dicionários).

SÓ LÊ, e de uma CÓPIA: a localização e a cópia da coleção vêm do próprio
anki_status.py (achar_fonte copia o arquivo e o -wal antes de abrir), para que
existam um jeito só de achar a coleção e um jeito só de errar.
"""
import importlib.util
import shutil
import sqlite3
import time
from contextlib import contextmanager
from datetime import date
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
        bandeira = [{"frente": _frente(f), "baralho": decks.get(did, "")}
                    for f, did in con.execute("""
                        SELECT n.flds, c.did FROM cards c JOIN notes n ON n.id = c.nid
                        WHERE c.flags & 7 != 0 ORDER BY c.mod DESC LIMIT 20""")]

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
