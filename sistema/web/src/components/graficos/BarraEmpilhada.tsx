import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

export interface ParteBarra {
  chave: string
  rotulo: string
  valor: number
  cor: string
  /** texto da dica; sem ele vai "rótulo: valor" */
  dica?: string
}

/**
 * Parte-do-todo numa barra só, horizontal. Feita em HTML (não Recharts) porque é
 * uma barra: segmentos proporcionais, 2 px de fundo separando um do outro (o
 * vão, não uma borda, é o que separa) e ponta arredondada só nas extremidades.
 * Sem número dentro do segmento: o pedaço pequeno não comporta, e o valor já
 * está na legenda logo abaixo.
 */
export function BarraEmpilhada({ partes, rotulo, altura = 14, className }: { partes: ParteBarra[]; rotulo: string; altura?: number; className?: string }) {
  const visiveis = partes.filter((p) => p.valor > 0)
  const total = visiveis.reduce((s, p) => s + p.valor, 0)
  if (total === 0) return <div className={cn('rounded bg-muted', className)} style={{ height: altura }} aria-label={`${rotulo}: vazio`} />
  return (
    <div
      role="img"
      aria-label={`${rotulo}: ${visiveis.map((p) => `${p.rotulo} ${p.valor}`).join(', ')}`}
      className={cn('flex w-full gap-[2px]', className)}
      style={{ height: altura }}
    >
      {visiveis.map((p, i) => (
        <Tooltip key={p.chave}>
          <TooltipTrigger asChild>
            <div
              className={cn(
                'h-full transition-[filter] hover:brightness-110',
                i === 0 && 'rounded-l-[4px]',
                i === visiveis.length - 1 && 'rounded-r-[4px]',
              )}
              // o mínimo de 3 px garante que um segmento de 1 em 2.000 ainda apareça
              style={{ flexGrow: p.valor, flexBasis: 0, minWidth: 3, background: p.cor }}
            />
          </TooltipTrigger>
          <TooltipContent>{p.dica ?? `${p.rotulo}: ${p.valor}`}</TooltipContent>
        </Tooltip>
      ))}
    </div>
  )
}
