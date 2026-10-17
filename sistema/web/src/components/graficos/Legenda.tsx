import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface ItemLegenda {
  chave: string
  rotulo: ReactNode
  cor: string
  /** o número ao lado do nome: é o que alivia as cores de pouco contraste */
  valor?: ReactNode
}

/** A amostra da série espelha a marca: retângulo para barra, traço para linha. */
export function Amostra({ cor, forma = 'barra' }: { cor: string; forma?: 'barra' | 'linha' }) {
  return forma === 'linha' ? (
    <span aria-hidden className="inline-block h-0.5 w-3 shrink-0 rounded-full" style={{ background: cor }} />
  ) : (
    <span aria-hidden className="inline-block size-2.5 shrink-0 rounded-[3px]" style={{ background: cor }} />
  )
}

/** Legenda em linha. O texto fica na tinta normal: a cor é da amostra, nunca da letra. */
export function Legenda({ itens, forma, className }: { itens: ItemLegenda[]; forma?: 'barra' | 'linha'; className?: string }) {
  return (
    <ul className={cn('flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground', className)}>
      {itens.map((i) => (
        <li key={i.chave} className="flex items-center gap-1.5">
          <Amostra cor={i.cor} forma={forma} />
          <span>{i.rotulo}</span>
          {i.valor !== undefined && <span className="font-medium text-foreground tabular-nums">{i.valor}</span>}
        </li>
      ))}
    </ul>
  )
}
