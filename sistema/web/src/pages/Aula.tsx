import { Link, useParams } from 'react-router'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { ErroCarga, Vazio } from '@/components/Estados'
import { useLicao, useLicaoAtual } from '@/api/queries'
import { ErroApi } from '@/api/client'
import { Runner } from '@/exercicios/Runner'

export function PaginaAula() {
  const { id } = useParams()
  return id ? <AulaPorId id={Number(id)} /> : <AulaAtual />
}

function AulaAtual() {
  const q = useLicaoAtual()
  if (q.isPending) return <Esqueleto />
  if (q.isError) return <ErroCarga erro={q.error} tentar={() => q.refetch()} />
  if (!q.data)
    return (
      <div className="mx-auto max-w-3xl">
        <Vazio>
          Nenhuma lição ainda. O tutor cria a lição de exercícios durante a aula no terminal (<code>/estudo</code>).
        </Vazio>
      </div>
    )
  return <Runner key={q.data.id} licao={q.data} />
}

function AulaPorId({ id }: { id: number }) {
  const q = useLicao(id)
  if (q.isPending) return <Esqueleto />
  if (q.isError) {
    if (q.error instanceof ErroApi && q.error.status === 404)
      return (
        <div className="mx-auto max-w-3xl space-y-4">
          <Vazio>A lição {id} não existe.</Vazio>
          <Button asChild variant="outline">
            <Link to="/aula">Ir para a lição atual</Link>
          </Button>
        </div>
      )
    return <ErroCarga erro={q.error} tentar={() => q.refetch()} />
  }
  return <Runner key={q.data.id} licao={q.data} />
}

function Esqueleto() {
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Skeleton className="h-6 w-2/3" />
      <Skeleton className="h-2 w-full" />
      <Skeleton className="h-8 w-80" />
      <Skeleton className="h-80 rounded-xl" />
    </div>
  )
}
