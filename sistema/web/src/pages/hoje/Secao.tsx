import type { ReactNode } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

/** Card padrão das seções da tela Hoje. */
export function Secao({
  titulo,
  icone,
  acao,
  children,
  className,
}: {
  titulo: ReactNode
  icone?: ReactNode
  acao?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <Card className={cn('gap-3', className)}>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-wide text-muted-foreground uppercase [&_svg]:size-4">
          {icone}
          {titulo}
        </CardTitle>
        {acao}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}
