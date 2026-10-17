"""Conexão com o estudo.db e migrações por PRAGMA user_version."""
import sqlite3
from pathlib import Path

from japones import config

ESQUEMA_ATUAL = 2
_DDL = Path(__file__).with_name("schema.sql")
_DDL2 = Path(__file__).with_name("schema2.sql")


def conectar(caminho: Path | None = None) -> sqlite3.Connection:
    caminho = Path(caminho or config.BANCO)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    _migrar(con)
    return con


def _migrar(con: sqlite3.Connection) -> None:
    (versao,) = con.execute("PRAGMA user_version").fetchone()
    if versao < 1:
        con.executescript(_DDL.read_text())
        con.execute("PRAGMA user_version = 1")
        con.commit()
        versao = 1
    if versao < 2:      # 17/10: lições e exercícios do painel (DESIGN §9)
        con.executescript(_DDL2.read_text())
        con.execute("PRAGMA user_version = 2")
        con.commit()
    # Esquemas futuros entram aqui, um `if versao < N` por vez, nunca editando os anteriores.


def linhas(cursor) -> list[dict]:
    return [dict(r) for r in cursor.fetchall()]
