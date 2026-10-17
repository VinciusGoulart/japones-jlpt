import { Layers } from 'lucide-react'
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Vazio } from '@/components/Estados'
import { Secao } from '@/pages/hoje/Secao'
import { inteiro } from '@/components/graficos/formato'
import type { BaralhoAnki } from '@/api/types'

const COLUNAS = [
  { chave: 'total', rotulo: 'Total' },
  { chave: 'novos', rotulo: 'Novos' },
  { chave: 'devidos', rotulo: 'Devidos' },
  { chave: 'aprendendo', rotulo: 'Aprendendo' },
  { chave: 'suspensos', rotulo: 'Suspensos' },
] as const

export function Baralhos({ baralhos }: { baralhos: BaralhoAnki[] }) {
  const soma = (k: (typeof COLUNAS)[number]['chave']) => baralhos.reduce((s, b) => s + b[k], 0)
  return (
    <Secao titulo="Baralhos" icone={<Layers />}>
      {baralhos.length === 0 ? (
        <Vazio>Nenhum baralho com cartões.</Vazio>
      ) : (
        <div className="-mx-4">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-4">Baralho</TableHead>
                {COLUNAS.map((c) => (
                  <TableHead key={c.chave} className="text-right last:pr-4">
                    {c.rotulo}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {baralhos.map((b) => {
                const partes = b.baralho.split('::')
                return (
                  <TableRow key={b.baralho}>
                    <TableCell className="pl-4">
                      {partes.length > 1 && <span className="text-muted-foreground">{partes.slice(0, -1).join(' › ')} › </span>}
                      <span className="font-medium">{partes[partes.length - 1]}</span>
                    </TableCell>
                    {COLUNAS.map((c) => (
                      <TableCell key={c.chave} className="text-right tabular-nums last:pr-4">
                        {b[c.chave] ? inteiro(b[c.chave]) : <span className="text-muted-foreground">0</span>}
                      </TableCell>
                    ))}
                  </TableRow>
                )
              })}
            </TableBody>
            {baralhos.length > 1 && (
              <TableFooter>
                <TableRow>
                  <TableCell className="pl-4">Todos</TableCell>
                  {COLUNAS.map((c) => (
                    <TableCell key={c.chave} className="text-right tabular-nums last:pr-4">
                      {inteiro(soma(c.chave))}
                    </TableCell>
                  ))}
                </TableRow>
              </TableFooter>
            )}
          </Table>
        </div>
      )}
    </Secao>
  )
}
