-- estudo.db — esquema 1. Contrato em sistema/DESIGN.md §4.
-- Toda data é o DIA DE ESTUDO (AAAA-MM-DD, vira às 04:00).

CREATE TABLE IF NOT EXISTS aula (
  id          INTEGER PRIMARY KEY,
  data        TEXT NOT NULL,                 -- não é única: 08/08 e 14/09 tiveram duas sessões
  dia_plano   INTEGER,                       -- o diário repete o número nos dias sem mesa
  tipo        TEXT NOT NULL CHECK (tipo IN ('completa', 'parcial', 'sem_mesa')),
  titulo      TEXT,
  fase        INTEGER,
  semana      INTEGER,
  inicio      TEXT,                          -- 'HH:MM' do relógio (pode ser madrugada do dia seguinte)
  minutos     INTEGER,
  verif_ok    INTEGER,
  verif_total INTEGER,
  prod_ok     INTEGER,
  prod_total  INTEGER,
  texto_md    TEXT NOT NULL,                 -- a entrada do diário, inteira
  origem      TEXT NOT NULL DEFAULT 'mcp' CHECK (origem IN ('migracao', 'mcp')),
  criado_em   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS aula_data ON aula(data);

CREATE TABLE IF NOT EXISTS trajeto (
  data           TEXT PRIMARY KEY,
  anki_cartoes   INTEGER,
  anki_minutos   REAL,
  audio          INTEGER CHECK (audio IN (0, 1)),   -- NULL = não informado
  audio_fonte    TEXT,                              -- 'teppei', 'anime', 'trello'…
  retencao_30d   REAL,
  fila_atrasados INTEGER,
  nota           TEXT
);

CREATE TABLE IF NOT EXISTS erro (
  id        INTEGER PRIMARY KEY,
  data      TEXT NOT NULL,
  bloco     TEXT NOT NULL CHECK (bloco IN ('abertura', 'verificacao', 'producao', 'diagnostico', 'anki', 'outro')),
  categoria TEXT NOT NULL,                  -- DESIGN §4.2
  escrito   TEXT,                           -- o que ele escreveu
  correto   TEXT,                           -- a forma corrigida
  porque    TEXT,                           -- a regra, em uma linha
  criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS erro_categoria ON erro(categoria, data);
CREATE INDEX IF NOT EXISTS erro_data ON erro(data);

CREATE TABLE IF NOT EXISTS padrao (
  id           INTEGER PRIMARY KEY,
  categoria    TEXT NOT NULL,
  descricao    TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'aberto' CHECK (status IN ('aberto', 'resolvido')),
  aberto_em    TEXT NOT NULL,
  resolvido_em TEXT,
  nota         TEXT
);

CREATE TABLE IF NOT EXISTS registro (
  id     INTEGER PRIMARY KEY,
  data   TEXT,                              -- tirada do prefixo DD/MM da entrada, quando houver
  texto  TEXT NOT NULL,
  origem TEXT NOT NULL                      -- 'pontos_fracos', 'vigiar'…
);

CREATE TABLE IF NOT EXISTS nota (
  chave         TEXT PRIMARY KEY,
  valor         TEXT NOT NULL,
  atualizado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
