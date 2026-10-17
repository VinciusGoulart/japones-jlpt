import { Ja } from '@/components/Ja'
import type { DetalheTexto } from '@/api/types'
import { cn } from '@/lib/utils'

/**
 * A resposta dele comparada com a aceita mais parecida, do ponto de vista dele:
 * "faltou" (estava na certa, ele não escreveu) em verde; "sobrou" (ele pôs a mais) riscado em vermelho.
 */
export function Diff({ detalhe }: { detalhe: Partial<DetalheTexto> }) {
  if (!detalhe.diff?.length) return null
  const igual = detalhe.diff.every((d) => d.op === 'igual')
  return (
    <div className="space-y-1.5">
      <p lang="ja" className="font-ja text-2xl leading-relaxed break-all">
        {detalhe.diff.map((d, i) => (
          <span
            key={i}
            className={cn(
              d.op === 'faltou' && 'rounded bg-ok-bg px-0.5 text-ok underline decoration-ok decoration-2 underline-offset-4',
              d.op === 'sobrou' && 'rounded bg-erro-bg px-0.5 text-erro line-through decoration-2',
            )}
            title={d.op === 'faltou' ? 'faltou' : d.op === 'sobrou' ? 'sobrou' : undefined}
          >
            {d.texto}
          </span>
        ))}
      </p>
      {detalhe.comparado_com && (
        <p className="text-sm text-muted-foreground">
          comparado com <Ja className="text-base text-foreground">{detalhe.comparado_com}</Ja>
          {!igual && (
            <span className="ml-2">
              · <span className="text-ok underline decoration-2 underline-offset-4">verde</span> = faltou ·{' '}
              <span className="text-erro line-through decoration-2">vermelho</span> = sobrou
            </span>
          )}
        </p>
      )}
    </div>
  )
}
