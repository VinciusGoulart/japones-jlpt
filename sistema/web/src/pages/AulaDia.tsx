import { Link, useParams } from 'react-router'
import { ArrowLeft, ChevronLeft, ChevronRight, Clock } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga, Vazio } from '@/components/Estados'
import { Markdown } from '@/components/Markdown'
import { useAula, useAulas } from '@/api/queries'
import { ErroApi } from '@/api/client'
import { dataCompleta, ddmm } from '@/lib/datas'
import { cn } from '@/lib/utils'
import { CLASSE_AULA, ROTULO_AULA, placar } from './calendario/tipos'

export function PaginaAulaDia() {
  const { data = '' } = useParams()
  const q = useAula(data)
  // a lista (já em cache se ele veio de /aulas) dá a aula anterior e a seguinte
  const lista = useAulas('')
  const datas = [...new Set((lista.data ?? []).map((a) => a.data))]
  const i = datas.indexOf(data)
  const anterior = i >= 0 ? datas[i + 1] : undefined
  const seguinte = i > 0 ? datas[i - 1] : undefined

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button asChild variant="ghost" size="sm" className="-ml-2 text-muted-foreground">
          <Link to="/aulas">
            <ArrowLeft /> Aulas
          </Link>
        </Button>
        <div className="flex gap-1">
          <Button asChild variant="outline" size="sm" disabled={!anterior} className={cn(!anterior && 'pointer-events-none opacity-40')}>
            <Link to={anterior ? `/aulas/${anterior}` : '#'}>
              <ChevronLeft /> {anterior ? ddmm(anterior) : 'anterior'}
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm" className={cn(!seguinte && 'pointer-events-none opacity-40')}>
            <Link to={seguinte ? `/aulas/${seguinte}` : '#'}>
              {seguinte ? ddmm(seguinte) : 'seguinte'} <ChevronRight />
            </Link>
          </Button>
        </div>
      </div>

      <h1 className="text-2xl font-semibold tracking-tight first-letter:uppercase">{data ? dataCompleta(data) : ''}</h1>

      {q.isPending ? (
        <div className="space-y-3">
          <Skeleton className="h-6 w-1/2" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      ) : q.isError ? (
        q.error instanceof ErroApi && q.error.status === 404 ? (
          <Vazio>Nenhuma aula registrada neste dia.</Vazio>
        ) : (
          <ErroCarga erro={q.error} tentar={() => q.refetch()} />
        )
      ) : (
        q.data.map((a) => (
          <Card key={a.id} className="gap-4">
            <CardContent className="space-y-4 px-5 sm:px-8">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm text-muted-foreground">
                <Badge className={cn('font-medium', CLASSE_AULA[a.tipo])}>{ROTULO_AULA[a.tipo]}</Badge>
                {a.dia_plano !== null && <span>dia {a.dia_plano} do plano</span>}
                {a.inicio && (
                  <span className="flex items-center gap-1">
                    <Clock className="size-3.5" /> {a.inicio}
                    {a.minutos ? ` · ${a.minutos} min` : ''}
                  </span>
                )}
                {placar(a.verif_ok, a.verif_total) && <span>verificação {placar(a.verif_ok, a.verif_total)}</span>}
                {placar(a.prod_ok, a.prod_total) && <span>produção {placar(a.prod_ok, a.prod_total)}</span>}
              </div>
              <Markdown texto={a.texto_md} className="text-[0.975rem]" />
            </CardContent>
          </Card>
        ))
      )}
    </div>
  )
}
