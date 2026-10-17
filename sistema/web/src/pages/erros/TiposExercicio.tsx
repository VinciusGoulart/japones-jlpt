import { Target } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Vazio } from '@/components/Estados'
import { Secao } from '@/pages/hoje/Secao'
import { BarraEmpilhada } from '@/components/graficos/BarraEmpilhada'
import { pctDeFracao } from '@/components/graficos/formato'
import type { ErrosPainel } from '@/api/types'
import { ROTULO_TIPO } from '@/exercicios/tipos'

/**
 * Acerto por tipo de exercício, contando só a PRIMEIRA resposta (a que conta,
 * DESIGN §9.2). O pior tipo vem primeiro: é ele que diz qual formato de
 * exercício ainda não fixa. `taxa_erro` null = nada fechado ainda (só produção
 * esperando o tutor), e aparece como tal, não como 0%.
 */
export function TiposExercicio({ tipos, dias }: { tipos: ErrosPainel['tipos_exercicio']; dias: number }) {
  const ordenados = [...tipos].sort((a, b) => (b.taxa_erro ?? -1) - (a.taxa_erro ?? -1) || b.respondidos - a.respondidos)
  return (
    <Secao titulo="Acerto por tipo de exercício" icone={<Target />}>
      {ordenados.length === 0 ? (
        <Vazio>
          Nenhum exercício respondido nos últimos {dias} dias. Quando ele fizer as lições da tela Aula, cada tipo (escolha, conjugue, ouça…) aparece
          aqui com o acerto da primeira resposta, o pior primeiro.
        </Vazio>
      ) : (
        <div className="-mx-4">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-4">Tipo</TableHead>
                <TableHead className="text-right">Feitos</TableHead>
                <TableHead className="w-40">Acerto</TableHead>
                <TableHead className="pr-4 text-right" title="produção ou digitação esperando a correção do tutor">
                  Com o tutor
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ordenados.map((t) => (
                <TableRow key={t.tipo}>
                  <TableCell className="pl-4 font-medium">{ROTULO_TIPO[t.tipo] ?? t.tipo}</TableCell>
                  <TableCell className="text-right tabular-nums">{t.respondidos}</TableCell>
                  <TableCell>
                    {t.taxa_erro === null ? (
                      <span className="text-xs text-muted-foreground">nada fechado ainda</span>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="w-9 text-right font-medium tabular-nums">{pctDeFracao(1 - t.taxa_erro)}</span>
                        <BarraEmpilhada
                          className="flex-1"
                          altura={8}
                          rotulo={`${ROTULO_TIPO[t.tipo] ?? t.tipo}: certos e errados`}
                          partes={[
                            { chave: 'certos', rotulo: 'certos', valor: t.certos, cor: 'var(--ok)', dica: `${t.certos} certos` },
                            { chave: 'errados', rotulo: 'errados', valor: t.errados, cor: 'var(--erro)', dica: `${t.errados} errados` },
                          ]}
                        />
                        <span className="text-xs text-muted-foreground tabular-nums">
                          {t.certos}/{t.certos + t.errados}
                        </span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="pr-4 text-right text-muted-foreground tabular-nums">{t.revisar || '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Secao>
  )
}
