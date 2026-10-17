import { Flame, Trophy, TriangleAlert } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga } from '@/components/Estados'
import { useHoje } from '@/api/queries'
import { dataLonga } from '@/lib/datas'
import { CardLicao } from './hoje/CardLicao'
import { CardPlano, CardLembrete } from './hoje/CardPlano'
import { CardPendencias, CardSemana } from './hoje/CardTrello'
import { CardAnki } from './hoje/CardAnki'
import { CardPadroes } from './hoje/CardPadroes'

export function PaginaHoje() {
  const q = useHoje()
  if (q.isPending) return <EsqueletoHoje />
  if (q.isError) return <ErroCarga erro={q.error} tentar={() => q.refetch()} />
  const h = q.data

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <p className="text-sm text-muted-foreground first-letter:uppercase">{dataLonga(h.dia_de_estudo)}</p>
        <h1 className="flex flex-wrap items-center gap-x-3 gap-y-1 text-2xl font-semibold tracking-tight sm:text-3xl">
          <span>Dia {h.dia_do_plano}</span>
          <span className="text-muted-foreground/50">·</span>
          <span className="flex items-center gap-1.5">
            <Flame className="size-6 text-aviso" /> streak {h.streak.atual_ate_ontem}
          </span>
          <span className="text-muted-foreground/50">·</span>
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Trophy className="size-5" /> recorde {h.streak.recorde}
          </span>
        </h1>
      </header>

      {h.avisos.length > 0 && (
        <div className="space-y-2">
          {h.avisos.map((a) => (
            <p key={a} className="flex items-start gap-2 rounded-lg border border-aviso/30 bg-aviso-bg px-4 py-2.5 text-sm">
              <TriangleAlert className="mt-0.5 size-4 shrink-0 text-aviso" />
              {a}
            </p>
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <CardLicao hoje={h.dia_de_estudo} />
          <CardPlano hoje={h} />
          {h.lembrete_abertura && <CardLembrete lembrete={h.lembrete_abertura} hoje={h.dia_de_estudo} />}
          <CardPadroes padroes={h.padroes_abertos} />
        </div>
        <div className="space-y-6">
          <CardPendencias trello={h.trello} hoje={h.dia_de_estudo} />
          <CardSemana trello={h.trello} />
          <CardAnki anki={h.anki} />
        </div>
      </div>
    </div>
  )
}

function EsqueletoHoje() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-9 w-96 max-w-full" />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Skeleton className="h-36 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-32 rounded-xl" />
        </div>
        <div className="space-y-6">
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-40 rounded-xl" />
          <Skeleton className="h-56 rounded-xl" />
        </div>
      </div>
    </div>
  )
}
