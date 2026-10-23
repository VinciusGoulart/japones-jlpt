"""Conexão com o estudo.db e migrações por PRAGMA user_version."""
import sqlite3
from pathlib import Path

from japones import config

ESQUEMA_ATUAL = 4
_DDL = Path(__file__).with_name("schema.sql")
_DDL2 = Path(__file__).with_name("schema2.sql")
_DDL3 = Path(__file__).with_name("schema3.sql")
_DDL4 = Path(__file__).with_name("schema4.sql")


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
        _refazer_exercicio(con, _DDL3, 3)
        versao = 3
    if versao < 4:      # 23/10: caderno de regras e o tipo 'explicacao' (DESIGN §13) — refeita de novo
        _refazer_exercicio(con, _DDL4, 4)
        versao = 4
    # Esquemas futuros entram aqui, um `if versao < N` por vez, nunca editando os anteriores.


def _refazer_exercicio(con: sqlite3.Connection, ddl: Path, versao: int) -> None:
    """Roda um esquema que refaz a tabela exercicio (o SQLite não altera CHECK).

    foreign_keys só muda fora de transação, e TEM de estar desligada: com ela ligada,
    o DROP TABLE exercicio apagaria em cascata todas as respostas (17/10, esquema 3)."""
    con.commit()
    con.execute("PRAGMA foreign_keys = OFF")
    try:
        con.executescript("BEGIN IMMEDIATE;\n" + ddl.read_text())
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError(f"esquema {versao}: a cópia da tabela exercicio quebrou uma chave estrangeira")
        con.execute(f"PRAGMA user_version = {versao}")
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.execute("PRAGMA foreign_keys = ON")


def linhas(cursor) -> list[dict]:
    return [dict(r) for r in cursor.fetchall()]
