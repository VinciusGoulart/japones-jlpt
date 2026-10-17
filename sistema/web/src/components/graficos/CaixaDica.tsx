import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface LinhaDica {
  chave: string
  valor: ReactNode
  rotulo: ReactNode
  /** a cor da série: vira um traço curto (não uma caixa) ao lado do valor */
  cor?: string
  /** linha de detalhe, recuada (ex.: os grupos dentro de uma família) */
  detalhe?: ReactNode
}

/**
 * O conteúdo da dica (tooltip) de qualquer gráfico daqui: título e, por linha,
 * o VALOR em destaque e o nome depois — o leitor já sabe a série, quer o número.
 */
export function CaixaDica({ titulo, linhas, rodape, className }: { titulo: ReactNode; linhas: LinhaDica[]; rodape?: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        'pointer-events-none min-w-36 max-w-64 rounded-lg bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md ring-1 ring-foreground/10',
        className,
      )}
    >
      <p className="mb-1 font-medium">{titulo}</p>
      <ul className="space-y-0.5">
        {linhas.map((l) => (
          <li key={l.chave}>
            <div className="flex items-center gap-1.5">
              {l.cor && <span aria-hidden className="inline-block h-0.5 w-2.5 shrink-0 rounded-full" style={{ background: l.cor }} />}
              <span className="font-semibold tabular-nums">{l.valor}</span>
              <span className="text-muted-foreground">{l.rotulo}</span>
            </div>
            {l.detalhe && <p className="pl-4 text-[11px] text-muted-foreground">{l.detalhe}</p>}
          </li>
        ))}
      </ul>
      {rodape && <p className="mt-1.5 border-t pt-1.5 text-[11px] text-muted-foreground">{rodape}</p>}
    </div>
  )
}
