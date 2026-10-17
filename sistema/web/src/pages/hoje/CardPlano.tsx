import { BellRing, CalendarClock, Route } from 'lucide-react'
import { Markdown } from '@/components/Markdown'
import type { Hoje } from '@/api/types'
import { ddmm, relativo } from '@/lib/datas'
import { Secao } from './Secao'

export function CardPlano({ hoje }: { hoje: Hoje }) {
  const u = hoje.ultima_aula
  return (
    <Secao titulo="Plano de hoje" icone={<Route />}>
      <div className="space-y-4">
        {hoje.plano_de_hoje ? (
          <Markdown texto={hoje.plano_de_hoje} className="text-base" />
        ) : (
          <p className="text-sm text-muted-foreground">O currículo não tem linha para hoje.</p>
        )}
        {u?.deixou_para_hoje && (
          <div className="space-y-1 rounded-lg border-l-3 border-primary/60 bg-muted/50 px-3 py-2">
            <p className="text-xs font-medium text-muted-foreground">
              A última aula deixou para hoje · dia {u.dia ?? '?'}, {ddmm(u.data)}
              {u.titulo ? ` — ${u.titulo}` : ''}
            </p>
            <Markdown texto={u.deixou_para_hoje} className="text-sm" />
          </div>
        )}
        {hoje.proximos.length > 0 && (
          <div className="space-y-1">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <CalendarClock className="size-3.5" /> Próximos dias
            </p>
            {hoje.proximos.map((p) => (
              <Markdown key={p} texto={p} className="text-sm text-muted-foreground" />
            ))}
          </div>
        )}
      </div>
    </Secao>
  )
}

export function CardLembrete({ lembrete, hoje }: { lembrete: NonNullable<Hoje['lembrete_abertura']>; hoje: string }) {
  const data = lembrete.de.slice(0, 10)
  return (
    <Secao
      titulo="Lembrete de abertura"
      icone={<BellRing />}
      acao={<span className="text-xs text-muted-foreground">anotado {relativo(data, hoje)} ({lembrete.de.slice(11, 16)})</span>}
    >
      <p className="text-sm leading-relaxed whitespace-pre-line">{lembrete.texto}</p>
    </Secao>
  )
}
