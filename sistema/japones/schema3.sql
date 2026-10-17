-- estudo.db — esquema 3: o tipo 'ouvir' (DESIGN §12). O SQLite não altera um CHECK,
-- então a tabela é refeita (receita "12 passos" da documentação do ALTER TABLE).
-- Roda com foreign_keys DESLIGADO (db._migrar cuida disso): com elas ligadas, o
-- DROP TABLE apagaria em cascata todas as respostas.

CREATE TABLE exercicio_novo (
  id         INTEGER PRIMARY KEY,
  licao_id   INTEGER NOT NULL REFERENCES licao(id) ON DELETE CASCADE,
  ordem      INTEGER NOT NULL,
  bloco      TEXT NOT NULL CHECK (bloco IN ('aquecimento', 'verificacao', 'producao', 'revisao')),
  tipo       TEXT NOT NULL CHECK (tipo IN ('escolha', 'achar_erro', 'ligar', 'ordenar', 'completar',
                                           'digitar', 'conjugar', 'ouvir', 'producao')),
  categoria  TEXT,
  enunciado  TEXT NOT NULL,
  dados      TEXT NOT NULL,                    -- JSON COM o gabarito: nunca vai inteiro para o navegador
  explicacao TEXT
);
INSERT INTO exercicio_novo (id, licao_id, ordem, bloco, tipo, categoria, enunciado, dados, explicacao)
  SELECT id, licao_id, ordem, bloco, tipo, categoria, enunciado, dados, explicacao FROM exercicio;
DROP TABLE exercicio;
ALTER TABLE exercicio_novo RENAME TO exercicio;
CREATE INDEX IF NOT EXISTS exercicio_licao ON exercicio(licao_id, ordem);
