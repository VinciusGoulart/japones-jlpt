import { ExternalLink, ListChecks, SquareKanban } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { FonteFora, Vazio } from '@/components/Estados'
import { ehErro, type ErroFonte, type ResumoTrello } from '@/api/types'
import { relativo } from '@/lib/datas'
import { cn } from '@/lib/utils'
import { Secao } from './Secao'

export function CardPendencias({ trello, hoje }: { trello: ResumoTrello | ErroFonte; hoje: string }) {
  return (
    <Secao titulo="Pendências do Trello" icone={<SquareKanban />}>
      {ehErro(trello) ? (
        <FonteFora nome="Trello" erro={trello.erro} />
      ) : (
        <div className="space-y-3">
          {trello.pendencias_7_dias.length === 0 ? (
            <Vazio>Nada vencendo nos próximos 7 dias.</Vazio>
          ) : (
            <ul className="space-y-2">
              {trello.pendencias_7_dias.map((p, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span
                    className={cn(
                      'mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-xs font-medium tabular-nums',
                      p.vencido ? 'bg-erro-bg text-erro' : p.vence === hoje ? 'bg-aviso-bg text-aviso' : 'bg-muted text-muted-foreground',
                    )}
                  >
                    {p.vence ? (p.vencido ? `venceu ${relativo(p.vence, hoje)}` : relativo(p.vence, hoje)) : 'sem data'}
                  </span>
                  <a
                    href={p.url ?? undefined}
                    target="_blank"
                    rel="noreferrer"
                    className={cn('min-w-0 hover:underline', p.vencido && 'text-erro')}
                  >
                    {p.nome}
                  </a>
                </li>
              ))}
            </ul>
          )}
          {trello.avisos_jlpt.length > 0 && (
            <div className="space-y-1.5 border-t pt-3">
              <p className="text-xs font-medium text-muted-foreground">Avisos do JLPT</p>
              {trello.avisos_jlpt.map((a, i) => (
                <a key={i} href={a.url ?? undefined} target="_blank" rel="noreferrer" className="flex items-start gap-1.5 text-sm hover:underline">
                  <ExternalLink className="mt-0.5 size-3.5 shrink-0 text-trello" />
                  {a.nome}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </Secao>
  )
}

export function CardSemana({ trello }: { trello: ResumoTrello | ErroFonte }) {
  return (
    <Secao titulo="Semana atual" icone={<ListChecks />}>
      {ehErro(trello) ? (
        <FonteFora nome="Trello" erro={trello.erro} />
      ) : trello.semana_atual.length === 0 ? (
        <Vazio>Nenhum card na lista da semana.</Vazio>
      ) : (
        <div className="space-y-4">
          {trello.semana_atual.map((c, i) => (
            <div key={i} className="space-y-2">
              <p className="text-sm font-medium">{c.card}</p>
              {c.checklists.map((cl, j) => {
                const [f, t] = cl.feitos.split('/').map(Number)
                return (
                  <div key={j} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{cl.nome}</span>
                      <span className={cn('tabular-nums', f === t && 'text-ok')}>{cl.feitos}</span>
                    </div>
                    {cl.faltam.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        <span className="text-xs text-muted-foreground">faltam:</span>
                        {cl.faltam.map((x) => (
                          <Badge key={x} variant="outline" className="font-normal">{x}</Badge>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-ok">completo ✓</p>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </Secao>
  )
}
