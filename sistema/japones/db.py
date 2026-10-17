"""Conexão com o estudo.db e migrações por PRAGMA user_version."""
import sqlite3
from pathlib import Path

from japones import config

ESQUEMA_ATUAL = 3
_DDL = Path(__file__).with_name("schema.sql")
_DDL2 = Path(__file__).with_name("schema2.sql")
_DDL3 = Path(__file__).with_name("schema3.sql")


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
        versao = 2
    if versao < 3:      # 17/10: o tipo 'ouvir' (DESIGN §12) — a tabela exercicio é refeita
        # foreign_keys só muda fora de transação, e TEM de estar desligada: com ela ligada,
        # o DROP TABLE exercicio apagaria em cascata todas as respostas.
        con.commit()
        con.execute("PRAGMA foreign_keys = OFF")
        try:
            con.executescript("BEGIN IMMEDIATE;\n" + _DDL3.read_text())
            if con.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("esquema 3: a cópia da tabela exercicio quebrou uma chave estrangeira")
            con.execute("PRAGMA user_version = 3")
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.execute("PRAGMA foreign_keys = ON")
    # Esquemas futuros entram aqui, um `if versao < N` por vez, nunca editando os anteriores.


def linhas(cursor) -> list[dict]:
    return [dict(r) for r in cursor.fetchall()]
