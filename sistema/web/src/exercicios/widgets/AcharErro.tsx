import { useState } from 'react'
import { Ja } from '@/components/Ja'
import { cn } from '@/lib/utils'
import type { PropsWidget } from '../tipos'

export function AcharErro({ render, resultado, onChange }: PropsWidget<'achar_erro'>) {
  const [sel, setSel] = useState<number | null>(null)
  const escolhido = resultado ? resultado.resposta.segmento : sel
  const errado = resultado?.detalhe.errado
  const correcao = resultado?.detalhe.correcao

  return (
    <div className="space-y-3">
      {/* a frase numa linha só, em segmentos clicáveis colados como texto corrido */}
      <p className="flex flex-wrap items-center gap-y-3 text-2xl leading-loose sm:text-3xl" lang="ja">
        {render.segmentos.map((s, i) => {
          const ehErrado = resultado && i === errado
          const marcado = escolhido === i
          return (
            <span key={i} className="inline-flex items-center">
              <button
                type="button"
                disabled={!!resultado}
                aria-pressed={marcado}
                onClick={() => {
                  setSel(i)
                  onChange({ segmento: i })
                }}
                className={cn(
                  'rounded-lg border-2 border-transparent px-1.5 py-0.5 font-ja transition-colors disabled:cursor-default',
                  !resultado && 'border-b-border hover:bg-accent',
                  !resultado && marcado && 'border-primary bg-accent',
                  ehErrado && 'text-erro line-through decoration-2',
                  resultado && marcado && !ehErrado && 'border-aviso border-dashed',
                  ehErrado && marcado && 'border-ok/60',
                )}
              >
                {s}
              </button>
              {ehErrado && correcao && (
                <Ja className="ml-1 rounded-lg bg-ok-bg px-1.5 py-0.5 font-medium text-ok">{correcao}</Ja>
              )}
            </span>
          )
        })}
      </p>
      {resultado && escolhido !== errado && escolhido !== null && escolhido !== undefined && (
        <p className="text-sm text-muted-foreground">
          Você marcou <Ja className="rounded border-2 border-dashed border-aviso px-1">{render.segmentos[escolhido]}</Ja>, que estava certo.
        </p>
      )}
    </div>
  )
}
