-- estudo.db — esquema 2: lições e exercícios do painel. Contrato em sistema/DESIGN.md §9.

CREATE TABLE IF NOT EXISTS licao (
  id           INTEGER PRIMARY KEY,
  data         TEXT NOT NULL,                  -- dia de estudo
  titulo       TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'aberta' CHECK (status IN ('aberta', 'concluida')),
  criada_em    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  concluida_em TEXT
);
CREATE INDEX IF NOT EXISTS licao_data ON licao(data);

CREATE TABLE IF NOT EXISTS exercicio (
  id         INTEGER PRIMARY KEY,
  licao_id   INTEGER NOT NULL REFERENCES licao(id) ON DELETE CASCADE,
  ordem      INTEGER NOT NULL,
  bloco      TEXT NOT NULL CHECK (bloco IN ('aquecimento', 'verificacao', 'producao', 'revisao')),
  tipo       TEXT NOT NULL CHECK (tipo IN ('escolha', 'achar_erro', 'ligar', 'ordenar', 'completar',
                                           'digitar', 'conjugar', 'producao')),
  categoria  TEXT,
  enunciado  TEXT NOT NULL,
  dados      TEXT NOT NULL,                    -- JSON COM o gabarito: nunca vai inteiro para o navegador
  explicacao TEXT
);
CREATE INDEX IF NOT EXISTS exercicio_licao ON exercicio(licao_id, ordem);

CREATE TABLE IF NOT EXISTS resposta (
  id           INTEGER PRIMARY KEY,
  exercicio_id INTEGER NOT NULL REFERENCES exercicio(id) ON DELETE CASCADE,
  resposta     TEXT NOT NULL,                  -- JSON, no formato do tipo
  veredito     TEXT NOT NULL CHECK (veredito IN ('certo', 'errado', 'revisar')),
  detalhe      TEXT,                           -- JSON
  correcao     TEXT,                           -- do tutor, ao fechar um 'revisar'
  tempo_ms     INTEGER,
  criado_em    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS resposta_exercicio ON resposta(exercicio_id, id);
