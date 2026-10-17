import { BookOpen, Check, Hourglass, X } from 'lucide-react'
import { Ja, TextoMisto } from '@/components/Ja'
import { Markdown } from '@/components/Markdown'
import type { Exercicio, Resultado } from '@/api/types'
import { cn } from '@/lib/utils'

const VEREDITO = {
  certo: { icone: Check, texto: 'Certo', classe: 'border-ok/40 bg-ok-bg text-ok' },
  errado: { icone: X, texto: 'Errado', classe: 'border-erro/40 bg-erro-bg text-erro' },
  revisar: { icone: Hourglass, texto: 'Enviado para o tutor — a correção aparece aqui', classe: 'border-aviso/40 bg-aviso-bg text-aviso' },
}

/** Correção na hora: veredito, gabarito e a regra — sempre reexplicada (pedido dele em 16/10). */
export function Feedback({ ex, resultado, treino }: { ex: Exercicio; resultado: Resultado; treino: boolean }) {
  const v = VEREDITO[resultado.veredito]
  const Icone = v.icone
  // no ordenar o widget já mostra "sua frase × gabarito"
  const mostrarGabarito = !!resultado.gabarito && ex.tipo !== 'ordenar'
  return (
    <div className="space-y-3" aria-live="polite">
      <div className={cn('flex items-center gap-2 rounded-xl border px-4 py-2.5 font-medium', v.classe)}>
        <Icone className="size-5 shrink-0" />
        <span>{v.texto}</span>
        {resultado.correcao && resultado.veredito !== 'revisar' && <span className="text-sm font-normal opacity-80">· corrigido pelo tutor</span>}
        {treino && <span className="ml-auto text-xs font-normal opacity-80">treino — não conta no placar</span>}
      </div>

      {mostrarGabarito && (
        <p className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-sm text-muted-foreground">Gabarito</span>
          <Ja className="text-xl font-medium">{resultado.gabarito}</Ja>
        </p>
      )}

      {resultado.explicacao && (
        <div className="flex gap-2.5 rounded-xl bg-muted/60 px-4 py-3">
          <BookOpen className="mt-0.5 size-4 shrink-0 text-primary" />
          <p className="text-base leading-relaxed">
            <TextoMisto texto={resultado.explicacao} classeJa="text-[1.15em]" />
          </p>
        </div>
      )}

      {resultado.correcao && (
        <div className="space-y-1.5 rounded-xl border bg-card px-4 py-3">
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Correção do tutor</p>
          <Markdown texto={resultado.correcao} className="text-base" />
        </div>
      )}
    </div>
  )
}
