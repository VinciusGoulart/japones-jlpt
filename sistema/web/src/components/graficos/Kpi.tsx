import type { ReactNode } from 'react'
import { TriangleAlert } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Um número de cabeçalho (stat tile): rótulo, valor grande, uma linha de
 * contexto e, se houver, o alerta. O alerta nunca é só cor: vem com ícone e
 * texto, porque é ele que manda mudar o que se faz amanhã.
 */
export function Kpi({
  rotulo,
  valor,
  unidade,
  sub,
  alerta,
  className,
  children,
}: {
  rotulo: string
  valor: ReactNode
  unidade?: string
  sub?: ReactNode
  alerta?: string | null
  className?: string
  children?: ReactNode
}) {
  return (
    <div className={cn('flex min-w-0 flex-col gap-1 rounded-xl bg-card p-4 ring-1 ring-foreground/10', className)}>
      <p className="text-xs font-medium text-muted-foreground">{rotulo}</p>
      <p className={cn('flex min-w-0 items-baseline gap-1.5 text-3xl leading-tight font-semibold tracking-tight', alerta && 'text-aviso')}>
        <span className="min-w-0 truncate">{valor}</span>
        {unidade && <span className="text-sm font-normal text-muted-foreground">{unidade}</span>}
      </p>
      {sub && <div className="text-xs leading-relaxed text-muted-foreground">{sub}</div>}
      {children}
      {alerta && (
        <p className="mt-auto flex items-start gap-1.5 rounded-md bg-aviso-bg px-2 py-1.5 text-xs font-medium text-aviso">
          <TriangleAlert className="mt-px size-3.5 shrink-0" />
          {alerta}
        </p>
      )}
    </div>
  )
}
