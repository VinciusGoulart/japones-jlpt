import { useState, type ReactNode } from 'react'
import { ChartColumn, Table2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

/**
 * O card de um gráfico: título no mesmo estilo das seções da tela Hoje, uma
 * linha de contexto e o botão que troca o gráfico pela tabela. A tabela é o
 * gêmeo acessível de todo gráfico: nenhum número fica preso a passar o mouse
 * nem a distinguir cor (algumas cores da paleta ficam abaixo de 3:1 no claro).
 */
export function CartaoGrafico({
  titulo,
  icone,
  descricao,
  acao,
  tabela,
  atualizando,
  className,
  children,
}: {
  titulo: ReactNode
  icone?: ReactNode
  descricao?: ReactNode
  acao?: ReactNode
  /** a mesma informação do gráfico, em tabela; sem ela o botão não aparece */
  tabela?: ReactNode
  /** recarregando: o gráfico anterior fica, esmaecido, em vez de piscar um esqueleto */
  atualizando?: boolean
  className?: string
  children: ReactNode
}) {
  const [verTabela, setVerTabela] = useState(false)
  return (
    <Card className={cn('gap-3', className)}>
      <CardHeader className="flex flex-col gap-1">
        <div className="flex w-full items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-wide text-muted-foreground uppercase [&_svg]:size-4">
            {icone}
            {titulo}
          </CardTitle>
          <div className="flex items-center gap-1">
            {acao}
            {tabela && (
              <Button variant="ghost" size="xs" onClick={() => setVerTabela((v) => !v)} aria-pressed={verTabela}>
                {verTabela ? <ChartColumn /> : <Table2 />}
                {verTabela ? 'Gráfico' : 'Tabela'}
              </Button>
            )}
          </div>
        </div>
        {descricao && <CardDescription className="text-xs leading-relaxed">{descricao}</CardDescription>}
      </CardHeader>
      <CardContent className={cn('min-w-0 transition-opacity', atualizando && 'opacity-60')}>
        {verTabela ? tabela : children}
      </CardContent>
    </Card>
  )
}
