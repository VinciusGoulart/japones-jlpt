import { useState, type ReactNode } from 'react'
import { AlarmClock, ChevronDown, CircleCheck, TriangleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga, Vazio } from '@/components/Estados'
import { TextoMisto } from '@/components/Ja'
import { Markdown } from '@/components/Markdown'
import { Kpi } from '@/components/graficos/Kpi'
import { inteiro, plural } from '@/components/graficos/formato'
import { Secao } from '@/pages/hoje/Secao'
import { useRegras } from '@/api/queries'
import type { Regra, StatusRegra } from '@/api/types'
import { ddmm } from '@/lib/datas'
import { cn } from '@/lib/utils'

const GRUPOS: { status: StatusRegra; titulo: string; icone: ReactNode; vazio: string }[] = [
  { status: 'vencida', titulo: 'Vencem hoje', icone: <AlarmClock />, vazio: 'Nenhuma regra para revisar hoje.' },
  { status: 'fragil', titulo: 'Frágeis', icone: <TriangleAlert />, vazio: 'Nenhuma regra com mais erros que acertos.' },
  { status: 'em_dia', titulo: 'Em dia', icone: <CircleCheck />, vazio: 'Nenhuma regra em dia ainda.' },
]

/** "vence hoje", "atrasada há 3 dias", "em 12 dias (04/11)" — pelo dia de estudo do servidor (regra das 04:00). */
function quando(r: Regra): string {
  if (r.dias === null || !r.proxima) return 'sem revisão marcada'
  if (r.dias < 0) return `atrasada há ${plural(-r.dias, 'dia', 'dias')}`
  if (r.dias === 0) return 'vence hoje'
  if (r.dias === 1) return `amanhã (${ddmm(r.proxima)})`
  return `em ${r.dias} dias (${ddmm(r.proxima)})`
}

function Numero({ rotulo, valor, classe }: { rotulo: string; valor: ReactNode; classe?: string }) {
  return (
    <div className="rounded-lg bg-muted/60 px-3 py-2">
      <p className="text-xs text-muted-foreground">{rotulo}</p>
      <p className={cn('text-sm font-medium tabular-nums', classe)}>{valor}</p>
    </div>
  )
}

function ItemRegra({ r }: { r: Regra }) {
  const [aberta, setAberta] = useState(false)
  const id = `regra-${r.slug}`
  return (
    <li className="py-3 first:pt-0 last:pb-0">
      <button
        type="button"
        onClick={() => setAberta((a) => !a)}
        aria-expanded={aberta}
        aria-controls={id}
        className="flex w-full items-start gap-3 rounded-md text-left outline-none hover:opacity-80 focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ChevronDown className={cn('mt-1 size-4 shrink-0 text-muted-foreground transition-transform', !aberta && '-rotate-90')} aria-hidden />
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-[15px] leading-relaxed font-medium">
            <TextoMisto texto={r.titulo} classeJa="text-base" />
          </p>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            {r.categoria && (
              <Badge variant="outline" className="font-mono text-xs">
                {r.categoria}
              </Badge>
            )}
            <span className={cn(r.status === 'vencida' && 'font-medium text-aviso')}>{quando(r)}</span>
            <span>
              · <span className="text-ok">{r.acertos} ✓</span> <span className={cn(r.erros > 0 && 'text-erro')}>{r.erros} ✗</span>
              {r.deslizes > 0 && <span className="text-aviso" title="deslizes: errou e corrigiu com a dica"> {r.deslizes} ↺</span>}
            </span>
          </div>
        </div>
      </button>

      {aberta && (
        <div id={id} className="mt-3 ml-7 space-y-3">
          {r.explicacao_md ? (
            <Markdown texto={r.explicacao_md} className="text-[0.975rem]" />
          ) : (
            <p className="text-sm text-muted-foreground">Esta regra ainda não tem explicação escrita.</p>
          )}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            <Numero rotulo="Acertos" valor={inteiro(r.acertos)} classe="text-ok" />
            <Numero rotulo="Erros" valor={inteiro(r.erros)} classe={r.erros ? 'text-erro' : undefined} />
            <Numero rotulo="Deslizes" valor={inteiro(r.deslizes)} classe={r.deslizes ? 'text-aviso' : undefined} />
            <Numero rotulo="Próxima revisão" valor={r.proxima ? ddmm(r.proxima) : '—'} />
            <Numero rotulo="Intervalo" valor={r.intervalo ? plural(r.intervalo, 'dia', 'dias') : 'ainda não revisada'} />
          </div>
          <p className="text-xs text-muted-foreground">
            {r.ensinada_em ? `Ensinada em ${ddmm(r.ensinada_em)}` : 'Data da aula não registrada'}
            {r.ultima_revisao && ` · última revisão ${ddmm(r.ultima_revisao)}`}
            {r.ultima_falha && ` · último erro ${ddmm(r.ultima_falha)}`}
          </p>
        </div>
      )}
    </li>
  )
}

/**
 * O caderno de regras (23/10/2026, pedido dele): cada regra de gramática ensinada, com a
 * agenda de revisão. Existe porque o vocabulário tinha o Anki e a gramática não tinha
 * nada — a regra era ensinada uma vez e só voltava se desse erro.
 */
export function PaginaRegras() {
  const q = useRegras()
  if (q.isError) return <ErroCarga erro={q.error} tentar={() => q.refetch()} />

  const grupo = (s: StatusRegra) => (q.data ?? []).filter((r) => r.status === s)
  const vencidas = grupo('vencida')
  const atrasadas = vencidas.filter((r) => (r.dias ?? 0) < 0).length

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Regras</h1>
        <p className="text-sm text-muted-foreground">
          O caderno de gramática: cada regra ensinada volta numa data marcada (2, 5, 12, 30, 60 dias). Um erro traz a regra de volta no dia
          seguinte.
        </p>
      </header>

      {q.isPending ? (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-3">
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-64 rounded-xl" />
        </div>
      ) : q.data.length === 0 ? (
        <Vazio>
          Nenhuma regra no caderno ainda. O tutor grava as regras com <code>salvar_regra</code> durante a aula, ou importa de uma vez com{' '}
          <code>python -m japones.regras importar</code>.
        </Vazio>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            <Kpi
              rotulo="Vencem hoje"
              valor={inteiro(vencidas.length)}
              sub={atrasadas ? `${plural(atrasadas, 'atrasada', 'atrasadas')}` : 'nenhuma atrasada'}
            />
            <Kpi rotulo="Frágeis" valor={inteiro(grupo('fragil').length)} sub="mais erros que acertos" />
            <Kpi rotulo="No caderno" valor={inteiro(q.data.length)} sub={`${plural(grupo('em_dia').length, 'em dia', 'em dia')}`} />
          </div>

          <div className="space-y-6">
            {GRUPOS.map((g) => {
              const lista = grupo(g.status)
              return (
                <Secao key={g.status} titulo={`${g.titulo} (${lista.length})`} icone={g.icone}>
                  {lista.length === 0 ? (
                    <Vazio>{g.vazio}</Vazio>
                  ) : (
                    <ul className="divide-y">
                      {lista.map((r) => (
                        <ItemRegra key={r.slug} r={r} />
                      ))}
                    </ul>
                  )}
                </Secao>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
