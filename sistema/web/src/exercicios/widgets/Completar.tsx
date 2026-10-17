import { useState } from 'react'
import { Check, X } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import type { PropsWidget } from '../tipos'

export function Completar({ render, resultado, onChange }: PropsWidget<'completar'>) {
  const n = render.partes.reduce((m, p) => (typeof p === 'string' ? m : Math.max(m, p.lacuna + 1)), 0)
  const [valores, setValores] = useState<string[]>(() => Array(n).fill(''))
  const [aberta, setAberta] = useState<number | null>(null)
  const atuais = resultado ? resultado.resposta.lacunas : valores
  const oks = resultado?.detalhe.lacunas

  const definir = (i: number, v: string) => {
    const novo = valores.map((x, j) => (j === i ? v : x))
    setValores(novo)
    onChange(novo.every((x) => x.trim()) ? { lacunas: novo.map((x) => x.trim()) } : null)
  }

  const estado = (i: number) =>
    !resultado || !oks ? '' : oks[i] ? 'border-ok bg-ok-bg text-ok' : 'border-erro bg-erro-bg text-erro'

  // o primeiro campo digitado ganha o foco (as lacunas com opções são clicadas)
  const primeiroCampo = render.partes.find((p) => typeof p !== 'string' && !p.opcoes?.length)
  return (
    <div>
      <p lang="ja" className="font-ja text-2xl leading-[2.4] sm:text-3xl sm:leading-[2.4]">
        {render.partes.map((p, k) => {
          if (typeof p === 'string') return <span key={k}>{p}</span>
          const i = p.lacuna
          const v = atuais[i] ?? ''
          const marca = resultado && oks && (oks[i] ? <Check className="inline size-4" /> : <X className="inline size-4" />)

          if (p.opcoes?.length) {
            return (
              <Popover key={k} open={aberta === i} onOpenChange={(o) => setAberta(o ? i : null)}>
                <PopoverTrigger asChild disabled={!!resultado}>
                  <button
                    type="button"
                    className={cn(
                      'mx-1 inline-flex min-w-[2.2em] items-center justify-center gap-1 rounded-lg border-2 px-2 align-middle leading-tight disabled:cursor-default',
                      v ? 'border-primary/50 bg-accent' : 'border-dashed border-muted-foreground/40 text-muted-foreground',
                      'py-1',
                      estado(i),
                    )}
                    aria-label={`lacuna ${i + 1}`}
                  >
                    {v || '？'}
                    {marca}
                  </button>
                </PopoverTrigger>
                {/* data-sem-enter: o Enter aqui escolhe a opção, não verifica */}
                <PopoverContent data-sem-enter className="w-auto p-2" align="center">
                  <div className="flex flex-wrap gap-1.5">
                    {p.opcoes.map((o) => (
                      <button
                        key={o}
                        type="button"
                        lang="ja"
                        onClick={() => {
                          definir(i, o)
                          setAberta(null)
                        }}
                        className={cn(
                          'min-w-11 rounded-lg border-2 px-3 py-1 font-ja text-2xl hover:border-primary/60 hover:bg-accent',
                          valores[i] === o && 'border-primary bg-accent',
                        )}
                      >
                        {o}
                      </button>
                    ))}
                  </div>
                </PopoverContent>
              </Popover>
            )
          }

          const foco = p === primeiroCampo && !resultado
          return (
            <span key={k} className="mx-1 inline-flex items-center gap-1 align-middle">
              <input
                type="text"
                lang="ja"
                autoFocus={foco}
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                disabled={!!resultado}
                value={v}
                onChange={(e) => definir(i, e.target.value)}
                aria-label={`lacuna ${i + 1}`}
                // largura acompanha o conteúdo: kana e kanji têm ~1em cada
                style={{ width: `${Math.max(2, [...v].length + 1)}em` }}
                className={cn(
                  'rounded-lg border-2 border-input bg-card px-1.5 py-0.5 text-center font-ja leading-tight outline-none focus:border-primary disabled:opacity-100',
                  estado(i),
                )}
              />
              {marca && <span className={oks?.[i] ? 'text-ok' : 'text-erro'}>{marca}</span>}
            </span>
          )
        })}
      </p>
    </div>
  )
}
