import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { Loader2, Search } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ErroCarga, Vazio } from '@/components/Estados'
import { TextoMisto } from '@/components/Ja'
import { useAulas } from '@/api/queries'
import { dataTabela, diaDaSemana } from '@/lib/datas'
import { useAtrasado } from '@/lib/useAtrasado'
import { cn } from '@/lib/utils'
import { CLASSE_AULA, ROTULO_AULA, placar } from './calendario/tipos'

export function PaginaAulas() {
  const [busca, setBusca] = useState('')
  const termo = useAtrasado(busca.trim(), 300)
  const q = useAulas(termo)
  const navegar = useNavigate()

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Aulas</h1>
        <div className="relative w-full sm:w-80">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="buscar no diário (ex.: に, forma て)"
            className="h-9 pl-9"
            aria-label="Buscar no texto do diário"
          />
          {q.isFetching && <Loader2 className="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />}
        </div>
      </div>

      {q.isError ? (
        <ErroCarga erro={q.error} tentar={() => q.refetch()} />
      ) : q.isPending ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-10" />)}
        </div>
      ) : q.data.length === 0 ? (
        <Vazio>{termo ? `Nenhuma aula com "${termo}".` : 'Nenhuma aula registrada.'}</Vazio>
      ) : (
        <div className={cn('rounded-xl border bg-card transition-opacity', q.isPlaceholderData && 'opacity-60')}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Data</TableHead>
                <TableHead className="text-right">Dia</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead className="w-full">Título</TableHead>
                <TableHead>Início</TableHead>
                <TableHead className="text-right">Verificação</TableHead>
                <TableHead className="pr-4 text-right">Produção</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {q.data.map((a, i) => (
                <TableRow key={`${a.data}-${i}`} className="cursor-pointer" onClick={() => navegar(`/aulas/${a.data}`)}>
                  <TableCell className="pl-4 whitespace-nowrap tabular-nums">
                    <Link to={`/aulas/${a.data}`} className="hover:underline" onClick={(e) => e.stopPropagation()}>
                      {dataTabela(a.data)}
                    </Link>
                    <span className="ml-1.5 text-xs text-muted-foreground">{diaDaSemana(a.data)}</span>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{a.dia_plano ?? '—'}</TableCell>
                  <TableCell>
                    <Badge className={cn('font-medium', CLASSE_AULA[a.tipo])}>{ROTULO_AULA[a.tipo]}</Badge>
                  </TableCell>
                  <TableCell className="max-w-0 truncate">
                    {a.titulo ? <TextoMisto texto={a.titulo} classeJa="text-[1.05em]" /> : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell className="tabular-nums text-muted-foreground">{a.inicio ?? '—'}</TableCell>
                  <TableCell className="text-right tabular-nums">{placar(a.verif_ok, a.verif_total) ?? '—'}</TableCell>
                  <TableCell className="pr-4 text-right tabular-nums">{placar(a.prod_ok, a.prod_total) ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      {q.data && q.data.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {q.data.length} aula{q.data.length > 1 ? 's' : ''}
          {termo ? ` com "${termo}"` : ''}
        </p>
      )}
    </div>
  )
}
