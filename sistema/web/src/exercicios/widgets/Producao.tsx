import { useState } from 'react'
import { Lightbulb } from 'lucide-react'
import { Textarea } from '@/components/ui/textarea'
import { Ja, TextoMisto } from '@/components/Ja'
import { cn } from '@/lib/utils'
import type { PropsWidget } from '../tipos'

const linhas = (t: string) => t.split('\n').map((l) => l.trim()).filter(Boolean)

export function Producao({ render, resultado, onChange }: PropsWidget<'producao'>) {
  const [texto, setTexto] = useState('')
  const n = linhas(texto).length
  const minimo = Math.max(1, render.minimo || 1)

  if (resultado) {
    return (
      <ol className="list-decimal space-y-1.5 pl-6 marker:text-sm marker:text-muted-foreground">
        {resultado.resposta.frases.map((f, i) => (
          <li key={i}>
            <Ja className="text-2xl leading-relaxed">{f}</Ja>
          </li>
        ))}
      </ol>
    )
  }

  return (
    <div className="space-y-3">
      {render.dicas.length > 0 && (
        <div className="flex items-start gap-2 text-sm text-muted-foreground">
          <Lightbulb className="mt-1 size-4 shrink-0 text-aviso" />
          <ul className="flex flex-wrap gap-1.5">
            {render.dicas.map((d) => (
              <li key={d} className="rounded-md bg-muted px-2 py-0.5">
                <TextoMisto texto={d} classeJa="text-base text-foreground" />
              </li>
            ))}
          </ul>
        </div>
      )}
      <Textarea
        lang="ja"
        autoFocus
        spellCheck={false}
        rows={Math.max(4, minimo + 1)}
        value={texto}
        placeholder="uma frase por linha"
        onChange={(e) => {
          setTexto(e.target.value)
          const fs = linhas(e.target.value)
          onChange(fs.length >= minimo ? { frases: fs } : null)
        }}
        className="min-h-40 font-ja text-2xl leading-relaxed md:text-2xl"
      />
      <p className={cn('text-sm text-muted-foreground tabular-nums', n >= minimo && 'text-ok')}>
        {n} de {minimo} frase{minimo > 1 ? 's' : ''} no mínimo
      </p>
    </div>
  )
}
