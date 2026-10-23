-- estudo.db — esquema 4: o caderno de regras de gramática e o tipo 'explicacao' (DESIGN §13).
-- 23/10/2026, pedido dele: a gramática não tinha agenda de revisão — cada regra era ensinada
-- uma vez e só voltava se desse erro. A tabela exercicio é refeita (o SQLite não altera um
-- CHECK) para aceitar o bloco 'novo', o tipo 'explicacao' e a coluna regra_id.
-- Roda com foreign_keys DESLIGADO (db._migrar cuida disso): com elas ligadas, o
-- DROP TABLE apagaria em cascata todas as respostas.

CREATE TABLE IF NOT EXISTS regra (
  id             INTEGER PRIMARY KEY,
  slug           TEXT UNIQUE NOT NULL,
  titulo         TEXT NOT NULL,
  categoria      TEXT,                          -- categoria de erro associada (§4.2), ex. 'gramatica:te-mo-ii'
  ensinada_em    TEXT,                          -- AAAA-MM-DD
  explicacao_md  TEXT,
  intervalo      REAL NOT NULL DEFAULT 0,       -- dias (§13.2)
  proxima        TEXT,                          -- dia de estudo da próxima revisão; NULL = sem agenda
  acertos        INTEGER NOT NULL DEFAULT 0,
  erros          INTEGER NOT NULL DEFAULT 0,
  ultima_revisao TEXT,
  ultima_falha   TEXT,
  criada_em      TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS regra_proxima ON regra(proxima);

CREATE TABLE exercicio_novo (
  id         INTEGER PRIMARY KEY,
  licao_id   INTEGER NOT NULL REFERENCES licao(id) ON DELETE CASCADE,
  ordem      INTEGER NOT NULL,
  bloco      TEXT NOT NULL CHECK (bloco IN ('aquecimento', 'novo', 'verificacao', 'producao', 'revisao')),
  tipo       TEXT NOT NULL CHECK (tipo IN ('escolha', 'achar_erro', 'ligar', 'ordenar', 'completar',
                                           'digitar', 'conjugar', 'ouvir', 'producao', 'explicacao')),
  categoria  TEXT,
  enunciado  TEXT NOT NULL,
  dados      TEXT NOT NULL,                    -- JSON COM o gabarito: nunca vai inteiro para o navegador
  explicacao TEXT,
  regra_id   INTEGER REFERENCES regra(id) ON DELETE SET NULL
);
INSERT INTO exercicio_novo (id, licao_id, ordem, bloco, tipo, categoria, enunciado, dados, explicacao)
  SELECT id, licao_id, ordem, bloco, tipo, categoria, enunciado, dados, explicacao FROM exercicio;
DROP TABLE exercicio;
ALTER TABLE exercicio_novo RENAME TO exercicio;
CREATE INDEX IF NOT EXISTS exercicio_licao ON exercicio(licao_id, ordem);
CREATE INDEX IF NOT EXISTS exercicio_regra ON exercicio(regra_id);
