-- estudo.db — esquema 5: a segunda tentativa com dica e o deslize (DESIGN §9.6 e §13.2).
-- 23/10/2026, recomendação do relatório de pesquisa aprovada por ele: dica que faz o aluno se
-- corrigir ensina mais que a resposta pronta (Lyster & Saito 2010), e o erro corrigido com a
-- dica (deslize) não pode zerar uma regra madura como o erro que ele não sabe corrigir (lacuna).
-- Só colunas novas: o SQLite acrescenta coluna sem refazer a tabela. db._migrar roda tudo numa
-- transação com a troca do user_version — ou entra tudo, ou nada.

ALTER TABLE exercicio ADD COLUMN dica_erro TEXT;              -- a dica da 2ª tentativa (§9.6)
ALTER TABLE resposta  ADD COLUMN apos_dica INTEGER NOT NULL DEFAULT 0 CHECK (apos_dica IN (0, 1));
                                                              -- 1 = 2ª tentativa ou desistência; 0 = 1ª ou "Praticar de novo"
ALTER TABLE erro      ADD COLUMN exercicio_id INTEGER REFERENCES exercicio(id) ON DELETE SET NULL;
ALTER TABLE erro      ADD COLUMN deslize INTEGER NOT NULL DEFAULT 0 CHECK (deslize IN (0, 1));
ALTER TABLE regra     ADD COLUMN deslizes INTEGER NOT NULL DEFAULT 0;   -- desde então `erros` conta só lacunas
ALTER TABLE regra     ADD COLUMN intervalo_dia REAL;                    -- o intervalo antes do 1º evento do dia ultima_revisao
ALTER TABLE regra     ADD COLUMN lacunas_dia INTEGER NOT NULL DEFAULT 0; -- lacunas no dia ultima_falha
CREATE INDEX IF NOT EXISTS erro_exercicio ON erro(exercicio_id);
