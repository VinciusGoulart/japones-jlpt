import { useEffect, useState } from 'react'
import { Check, X } from 'lucide-react'
import { Ja } from '@/components/Ja'
import { normalizar } from '@/lib/texto'
import { cn } from '@/lib/utils'
import type { PropsWidget } from '../tipos'

export function Escolha({ render, resultado, onChange }: PropsWidget<'escolha'>) {
  const [sel, setSel] = useState<string | null>(null)
  const escolhida = resultado ? resultado.resposta.opcao : sel
  const curtas = render.opcoes.every((o) => [...o].length <= 6)

  const escolher = (o: string) => {
    if (resultado) return
    setSel(o)
    onChange({ opcao: o })
  }

  // teclas 1–9 escolhem a opção (fora de campos de texto)
  useEffect(() => {
    if (resultado) return
    const onKey = (e: KeyboardEvent) => {
      const alvo = e.target as HTMLElement | null
      if (alvo && (alvo.tagName === 'INPUT' || alvo.tagName === 'TEXTAREA')) return
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const n = Number(e.key)
      if (Number.isInteger(n) && n >= 1 && n <= render.opcoes.length) {
        e.preventDefault()
        const o = render.opcoes[n - 1]
        setSel(o)
        onChange({ opcao: o })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [resultado, render.opcoes, onChange])

  return (
    <div className={cn('grid gap-2.5', curtas ? 'grid-cols-2 sm:grid-cols-4' : 'grid-cols-1')} role="radiogroup">
      {render.opcoes.map((o, i) => {
        const marcada = escolhida === o
        const certa = resultado && normalizar(o) === normalizar(resultado.gabarito)
        const errada = resultado && marcada && !certa
        return (
          <button
            key={o}
            type="button"
            role="radio"
            aria-checked={marcada}
            disabled={!!resultado}
            onClick={() => escolher(o)}
            className={cn(
              'group flex items-center gap-3 rounded-xl border-2 bg-card px-4 py-3 text-left transition-colors',
              !resultado && 'hover:border-primary/50 hover:bg-accent/50',
              !resultado && marcada && 'border-primary bg-accent',
              certa && 'border-ok bg-ok-bg',
              errada && 'border-erro bg-erro-bg',
              resultado && !certa && !errada && 'opacity-55',
              'disabled:cursor-default',
            )}
          >
            <span
              className={cn(
                'flex size-6 shrink-0 items-center justify-center rounded-md border text-xs font-medium text-muted-foreground tabular-nums',
                marcada && !resultado && 'border-primary bg-primary text-primary-foreground',
                certa && 'border-ok bg-ok text-background',
                errada && 'border-erro bg-erro text-background',
              )}
            >
              {certa ? <Check className="size-4" /> : errada ? <X className="size-4" /> : i + 1}
            </span>
            <Ja className={cn('text-2xl leading-snug', curtas && 'mx-auto pr-6')}>{o}</Ja>
          </button>
        )
      })}
    </div>
  )
}
