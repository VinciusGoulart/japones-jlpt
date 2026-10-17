import { Link } from 'react-router'
import { ArrowRight, Check, Clock, NotebookPen, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga } from '@/components/Estados'
import { TextoMisto } from '@/components/Ja'
import { useLicaoAtual } from '@/api/queries'
import { ddmm } from '@/lib/datas'

/** O botão principal da tela: a lição que o tutor criou para hoje. */
export function CardLicao({ hoje }: { hoje: string }) {
  const q = useLicaoAtual()
  if (q.isPending) return <Skeleton className="h-36 rounded-xl" />
  if (q.isError) return <ErroCarga erro={q.error} tentar={() => q.refetch()} />
  const l = q.data
  if (!l)
    return (
      <Card className="border-dashed bg-transparent ring-0 outline outline-1 outline-dashed outline-border">
        <CardContent className="flex items-center gap-3 text-sm text-muted-foreground">
          <NotebookPen className="size-5 shrink-0" />
          Nenhuma lição ainda. O tutor cria a lição de exercícios durante a aula no terminal.
        </CardContent>
      </Card>
    )

  const total = l.exercicios.length
  const feitos = l.exercicios.filter((e) => e.resultado).length
  const conta = (v: string) => l.exercicios.filter((e) => e.resultado?.veredito === v).length
  const deHoje = l.data === hoje
  const rotulo = deHoje
    ? feitos === 0
      ? 'Aula de hoje'
      : feitos < total
        ? 'Continuar a aula de hoje'
        : 'Ver a aula de hoje'
    : l.status === 'aberta'
      ? `Continuar a lição de ${ddmm(l.data)}`
      : `Rever a lição de ${ddmm(l.data)}`

  return (
    <Card className="gap-4 bg-linear-to-br from-accent/70 to-card">
      <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1 space-y-2">
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {deHoje ? 'Lição de hoje' : `Lição de ${ddmm(l.data)}`} · {feitos} de {total} feitos
          </p>
          <h2 className="text-lg leading-snug font-semibold">
            <TextoMisto texto={l.titulo} />
          </h2>
          <Progress value={total ? (feitos / total) * 100 : 0} className="h-2" />
          {feitos > 0 && (
            <p className="flex gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1 text-ok"><Check className="size-4" />{conta('certo')}</span>
              <span className="flex items-center gap-1 text-erro"><X className="size-4" />{conta('errado')}</span>
              {conta('revisar') > 0 && (
                <span className="flex items-center gap-1 text-aviso"><Clock className="size-4" />{conta('revisar')} com o tutor</span>
              )}
            </p>
          )}
        </div>
        <Button asChild size="lg" className="h-11 px-5 text-base">
          <Link to={deHoje ? '/aula' : `/aula/${l.id}`}>
            {rotulo} <ArrowRight />
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}
