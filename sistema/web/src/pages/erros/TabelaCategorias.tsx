import { Fragment, useMemo } from 'react'
import { ListFilter } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Vazio } from '@/components/Estados'
import { Secao } from '@/pages/hoje/Secao'
import type { ErrosPainel } from '@/api/types'
import { ddmm, relativo } from '@/lib/datas'
import { cn } from '@/lib/utils'
import { familiaDe } from './familias'

type Categoria = ErrosPainel['por_categoria'][number]

interface Grupo {
  grupo: string
  n: number
  ultimo: string
  categorias: Categoria[]
}

function agrupar(cats: Categoria[]): Grupo[] {
  const mapa = new Map<string, Grupo>()
  for (const c of cats) {
    const g = mapa.get(c.grupo) ?? { grupo: c.grupo, n: 0, ultimo: c.ultimo, categorias: [] }
    g.n += c.n
    if (c.ultimo > g.ultimo) g.ultimo = c.ultimo
    g.categorias.push(c)
    mapa.set(c.grupo, g)
  }
  return [...mapa.values()].sort((a, b) => b.n - a.n || b.ultimo.localeCompare(a.ultimo))
}

/**
 * As categorias do período, agrupadas pelo prefixo. Clicar filtra a lista de
 * erros: a categoria filtra por ela, o grupo filtra por todas as do grupo (o
 * filtro da API é por prefixo, DESIGN §6). Clicar de novo no filtro ativo limpa.
 */
export function TabelaCategorias({
  porCategoria,
  filtro,
  onFiltrar,
  hoje,
  atualizando,
}: {
  porCategoria: ErrosPainel['por_categoria']
  filtro: string
  onFiltrar: (categoria: string) => void
  hoje: string
  atualizando: boolean
}) {
  const grupos = useMemo(() => agrupar(porCategoria), [porCategoria])
  const maior = Math.max(1, ...grupos.map((g) => g.n))

  const linha = (chave: string, rotulo: string, n: number, ultimo: string, grupo: string, nivel: 'grupo' | 'sub' | 'unica') => {
    const ativo = filtro === chave
    const cor = familiaDe(grupo).cor
    return (
      <TableRow
        key={`${nivel}-${chave}`}
        onClick={() => onFiltrar(ativo ? '' : chave)}
        className={cn('cursor-pointer', ativo && 'bg-accent hover:bg-accent')}
      >
        <TableCell className={cn('max-w-0 pl-3', nivel === 'sub' && 'pl-8')}>
          {/* o botão é o alvo do teclado; o clique dele sobe até a linha */}
          <button
            type="button"
            aria-pressed={ativo}
            className="flex w-full min-w-0 items-center gap-2 rounded-sm text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {nivel !== 'sub' && <span aria-hidden className="size-2.5 shrink-0 rounded-[3px]" style={{ background: cor }} />}
            <span className={cn('truncate font-mono text-[13px]', nivel === 'grupo' && 'font-semibold')}>{rotulo}</span>
          </button>
        </TableCell>
        <TableCell className="w-24">
          <div className="flex items-center gap-2">
            <span className={cn('w-5 text-right tabular-nums', nivel === 'grupo' && 'font-semibold')}>{n}</span>
            {nivel !== 'sub' && (
              <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                <span className="block h-full rounded-full" style={{ width: `${(n / maior) * 100}%`, background: cor }} />
              </span>
            )}
          </div>
        </TableCell>
        <TableCell className="w-14 pr-3 text-right text-xs text-muted-foreground tabular-nums" title={relativo(ultimo, hoje)}>
          {ddmm(ultimo)}
        </TableCell>
      </TableRow>
    )
  }

  return (
    <Secao
      titulo="Categorias"
      icone={<ListFilter />}
      className={cn('transition-opacity', atualizando && 'opacity-60')}
      acao={<span className="text-xs text-muted-foreground">clique para filtrar</span>}
    >
      {grupos.length === 0 ? (
        <Vazio>Sem categorias no período.</Vazio>
      ) : (
        <div className="-mx-4">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-3">Categoria</TableHead>
                <TableHead>Erros</TableHead>
                <TableHead className="pr-3 text-right">Último</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {grupos.map((g) =>
                g.categorias.length === 1 ? (
                  linha(g.categorias[0].categoria, g.categorias[0].categoria, g.n, g.ultimo, g.grupo, 'unica')
                ) : (
                  <Fragment key={g.grupo}>
                    {linha(g.grupo, g.grupo, g.n, g.ultimo, g.grupo, 'grupo')}
                    {g.categorias.map((c) => linha(c.categoria, c.categoria.slice(g.grupo.length) || c.categoria, c.n, c.ultimo, g.grupo, 'sub'))}
                  </Fragment>
                ),
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </Secao>
  )
}
