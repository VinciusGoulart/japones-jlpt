import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { BookOpenText, ExternalLink, Headphones, Layers, NotebookPen, Route } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Markdown } from '@/components/Markdown'
import { TextoMisto } from '@/components/Ja'
import type { DiaCalendario, EventoTrello } from '@/api/types'
import { cn } from '@/lib/utils'
import { CLASSE_AULA, ROTULO_AULA, placar } from './tipos'

function Bloco({ titulo, icone, children }: { titulo: string; icone: ReactNode; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-muted-foreground uppercase [&_svg]:size-3.5">
        {icone}
        {titulo}
      </h3>
      {children}
    </section>
  )
}

/** O painel lateral de um dia do calendário. */
export function DiaDetalhe({ dia, trello }: { dia: DiaCalendario | undefined; trello: EventoTrello[] }) {
  if (!dia) return <p className="text-sm text-muted-foreground">Sem dados para este dia.</p>
  const t = dia.trajeto
  return (
    <div className="space-y-5">
      <Bloco titulo="Mesa" icone={<BookOpenText />}>
        {dia.aulas.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhuma aula registrada.</p>
        ) : (
          <div className="space-y-3">
            {dia.aulas.map((a, i) => (
              <div key={i} className="space-y-1.5 rounded-lg border p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className={cn('font-medium', CLASSE_AULA[a.tipo])}>{ROTULO_AULA[a.tipo]}</Badge>
                  {a.dia_plano !== null && <span className="text-xs text-muted-foreground">dia {a.dia_plano} do plano</span>}
                </div>
                {a.titulo && (
                  <p className="text-sm font-medium">
                    <TextoMisto texto={a.titulo} classeJa="text-base" />
                  </p>
                )}
                {(placar(a.verif_ok, a.verif_total) || placar(a.prod_ok, a.prod_total)) && (
                  <p className="flex gap-4 text-xs text-muted-foreground tabular-nums">
                    {placar(a.verif_ok, a.verif_total) && <span>verificação {placar(a.verif_ok, a.verif_total)}</span>}
                    {placar(a.prod_ok, a.prod_total) && <span>produção {placar(a.prod_ok, a.prod_total)}</span>}
                  </p>
                )}
              </div>
            ))}
            <Link to={`/aulas/${dia.data}`} className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
              Ler a entrada do diário →
            </Link>
          </div>
        )}
      </Bloco>

      <Separator />

      <Bloco titulo="Trajeto" icone={<Layers />}>
        {!t ? (
          <p className="text-sm text-muted-foreground">Não registrado.</p>
        ) : (
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-muted/60 p-2">
              <p className="text-lg font-semibold tabular-nums">{t.anki_cartoes ?? '—'}</p>
              <p className="text-xs text-muted-foreground">cartões</p>
            </div>
            <div className="rounded-lg bg-muted/60 p-2">
              <p className="text-lg font-semibold tabular-nums">{t.anki_minutos !== null ? Math.round(t.anki_minutos) : '—'}</p>
              <p className="text-xs text-muted-foreground">min de Anki</p>
            </div>
            <div className={cn('rounded-lg p-2', t.audio === 1 ? 'bg-ok-bg text-ok' : 'bg-muted/60')}>
              <Headphones className="mx-auto size-5" />
              <p className="text-xs">{t.audio === 1 ? 'áudio feito' : t.audio === 0 ? 'sem áudio' : 'áudio ?'}</p>
            </div>
          </div>
        )}
      </Bloco>

      {dia.plano && (
        <>
          <Separator />
          <Bloco titulo="Plano" icone={<Route />}>
            <Markdown texto={dia.plano} className="text-sm" />
          </Bloco>
        </>
      )}

      {dia.licoes.length > 0 && (
        <>
          <Separator />
          <Bloco titulo="Lições" icone={<NotebookPen />}>
            <ul className="space-y-1.5">
              {dia.licoes.map((l) => (
                <li key={l.id}>
                  <Link to={`/aula/${l.id}`} className="flex items-center gap-2 text-sm text-licao hover:underline">
                    <TextoMisto texto={l.titulo} />
                    <Badge variant="outline" className="font-normal">{l.status === 'aberta' ? 'aberta' : 'concluída'}</Badge>
                  </Link>
                </li>
              ))}
            </ul>
          </Bloco>
        </>
      )}

      {trello.length > 0 && (
        <>
          <Separator />
          <Bloco titulo="Prazos do Trello" icone={<ExternalLink />}>
            <ul className="space-y-1.5">
              {trello.map((e, i) => (
                <li key={i} className="text-sm">
                  <a href={e.url ?? undefined} target="_blank" rel="noreferrer" className={cn('text-trello hover:underline', e.concluido && 'line-through opacity-60')}>
                    {e.nome}
                  </a>
                  <span className="ml-1.5 text-xs text-muted-foreground">({e.lista})</span>
                </li>
              ))}
            </ul>
          </Bloco>
        </>
      )}
    </div>
  )
}
