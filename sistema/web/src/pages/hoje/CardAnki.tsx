import { Flag, Layers, Repeat, TriangleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { FonteFora } from '@/components/Estados'
import { Ja } from '@/components/Ja'
import { ehErro, type ErroFonte, type ResumoAnki } from '@/api/types'
import { cn } from '@/lib/utils'
import { Secao } from './Secao'

function Numero({ rotulo, valor, sub, alerta }: { rotulo: string; valor: string; sub?: string; alerta?: boolean }) {
  return (
    <div className="rounded-lg bg-muted/60 px-3 py-2">
      <p className="text-xs text-muted-foreground">{rotulo}</p>
      <p className={cn('text-xl font-semibold tabular-nums', alerta && 'text-aviso')}>{valor}</p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  )
}

export function CardAnki({ anki }: { anki: ResumoAnki | ErroFonte }) {
  if (ehErro(anki))
    return (
      <Secao titulo="Anki" icone={<Layers />}>
        <FonteFora nome="Anki" erro={anki.erro} />
      </Secao>
    )
  const alertas = [anki.alerta_fila && `Fila: ${anki.alerta_fila}`, anki.alerta_retencao && `Retenção ${anki.alerta_retencao}`].filter(
    (x): x is string => !!x,
  )
  return (
    <Secao titulo="Anki" icone={<Layers />} acao={<span className="text-xs text-muted-foreground">{anki.leitura}</span>}>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <Numero rotulo="Hoje" valor={`${anki.hoje.cartoes}`} sub={`cartões · ${anki.hoje.minutos} min`} />
          <Numero rotulo="Ontem" valor={`${anki.ontem.cartoes}`} sub={`cartões · ${anki.ontem.minutos} min`} />
          <Numero rotulo="Fila atrasada" valor={`${anki.fila_atrasados}`} alerta={!!anki.alerta_fila} />
          <Numero
            rotulo="Retenção 30 dias"
            valor={anki.retencao_30d === null ? '—' : `${anki.retencao_30d.toLocaleString('pt-BR')}%`}
            alerta={!!anki.alerta_retencao}
          />
        </div>
        {alertas.map((a) => (
          <p key={a} className="flex items-start gap-2 rounded-md bg-aviso-bg px-3 py-2 text-sm text-aviso">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            {a}
          </p>
        ))}
        {anki.em_loop.length > 0 && (
          <div className="space-y-1.5">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Repeat className="size-3.5" /> Em loop (7 dias)
            </p>
            <div className="flex flex-wrap gap-1.5">
              {anki.em_loop.map((x) => (
                <Badge key={x} variant="secondary" className="h-auto py-0.5 text-sm font-normal">
                  <Ja>{x}</Ja>
                </Badge>
              ))}
            </div>
          </div>
        )}
        {anki.bandeira.length > 0 && (
          <div className="space-y-1.5">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Flag className="size-3.5" /> Com bandeira
            </p>
            <ul className="space-y-0.5 text-sm">
              {anki.bandeira.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Secao>
  )
}
