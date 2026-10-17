"""Conexão com o estudo.db e migrações por PRAGMA user_version."""
import sqlite3
from pathlib import Path

from japones import config

ESQUEMA_ATUAL = 1
_DDL = Path(__file__).with_name("schema.sql")


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
    # Esquemas futuros entram aqui, um `if versao < N` por vez, nunca editando o 1.


def linhas(cursor) -> list[dict]:
    return [dict(r) for r in cursor.fetchall()]
