import { useState } from 'react'
import { Lightbulb } from 'lucide-react'
import { Ja, TextoMisto } from '@/components/Ja'
import type { DetalheTexto, RespostaTexto, Veredito } from '@/api/types'
import { cn } from '@/lib/utils'
import type { PropsWidget } from '../tipos'
import { Diff } from './Diff'

/** O que o campo precisa da correção. Digitar e conjugar passam o Resultado inteiro; o ditado do ouvir monta este recorte. */
export interface CorrecaoTexto {
  veredito: Veredito
  resposta: RespostaTexto
  detalhe: Partial<DetalheTexto>
}

/** Campo de japonês (mozc) com a correção embaixo. Exportado para o ditado do ouvir digitar com a mesma regra. */
export function CampoTexto({
  resultado,
  onChange,
  placeholder,
}: {
  resultado: CorrecaoTexto | null
  onChange: (r: RespostaTexto | null) => void
  placeholder: string
}) {
  const [texto, setTexto] = useState('')
  return (
    <div className="space-y-3">
      <input
        type="text"
        lang="ja"
        autoFocus={!resultado}
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        disabled={!!resultado}
        placeholder={placeholder}
        value={resultado ? resultado.resposta.texto : texto}
        onChange={(e) => {
          setTexto(e.target.value)
          onChange(e.target.value.trim() ? { texto: e.target.value } : null)
        }}
        className={cn(
          'h-14 w-full rounded-xl border-2 border-input bg-card px-4 font-ja text-2xl outline-none placeholder:text-base placeholder:text-muted-foreground/70 focus:border-primary disabled:opacity-100',
          resultado?.veredito === 'certo' && 'border-ok bg-ok-bg',
          resultado?.veredito === 'errado' && 'border-erro bg-erro-bg',
          resultado?.veredito === 'revisar' && 'border-aviso bg-aviso-bg',
        )}
      />
      {resultado && <Diff detalhe={resultado.detalhe} />}
    </div>
  )
}

export function Digitar({ render, resultado, onChange }: PropsWidget<'digitar'>) {
  return (
    <div className="space-y-3">
      {render.dica && (
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <Lightbulb className="mt-0.5 size-4 shrink-0 text-aviso" />
          <span>
            Dica: <TextoMisto texto={render.dica} classeJa="text-base text-foreground" />
          </span>
        </p>
      )}
      <CampoTexto resultado={resultado} onChange={onChange} placeholder="digite em japonês (mozc)" />
    </div>
  )
}

export function Conjugar({ render, resultado, onChange }: PropsWidget<'conjugar'>) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 rounded-xl bg-muted/50 py-5">
        {/* a leitura vai inteira em cima, não como furigana: ruby espalharia いく sobre o く do okurigana */}
        <span className="flex flex-col items-center">
          {render.leitura && render.leitura !== render.verbo && (
            <Ja className="text-lg text-muted-foreground">{render.leitura}</Ja>
          )}
          <Ja className="text-5xl leading-tight font-medium">{render.verbo}</Ja>
        </span>
        <span className="text-muted-foreground">→</span>
        <span className="rounded-lg bg-primary/10 px-3 py-1 text-lg font-medium text-primary">
          <TextoMisto texto={render.forma} />
        </span>
      </div>
      <CampoTexto resultado={resultado} onChange={onChange} placeholder="a forma pedida" />
    </div>
  )
}
