import { useSearchParams } from 'react-router'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga } from '@/components/Estados'
import { Kpi } from '@/components/graficos/Kpi'
import { inteiro, pctDeFracao, plural } from '@/components/graficos/formato'
import { useErrosPainel } from '@/api/queries'
import type { ErroRegistrado, ErrosPainel } from '@/api/types'
import { dataTabela, diaDeEstudoLocal, diasEntre, paraIso } from '@/lib/datas'
import { cn } from '@/lib/utils'
import { ErrosPorSemana } from './erros/ErrosPorSemana'
import { ListaErros } from './erros/ListaErros'
import { Padroes } from './erros/Padroes'
import { RegistroAntigo } from './erros/RegistroAntigo'
import { TabelaCategorias } from './erros/TabelaCategorias'
import { TiposExercicio } from './erros/TiposExercicio'

const PERIODOS = [
  { dias: 30, rotulo: '30 dias' },
  { dias: 90, rotulo: '90 dias' },
  { dias: 365, rotulo: '1 ano' },
] as const
const PADRAO = 90

const ROTULO_BLOCO: [ErroRegistrado['bloco'], string][] = [
  ['abertura', 'na abertura'],
  ['verificacao', 'na verificação'],
  ['producao', 'na produção'],
  ['diagnostico', 'no diagnóstico'],
  ['anki', 'no Anki'],
  ['outro', 'em outro bloco'],
]

function SeletorPeriodo({ dias, onChange }: { dias: number; onChange: (d: number) => void }) {
  return (
    <div role="radiogroup" aria-label="Período" className="inline-flex rounded-lg bg-muted p-[3px]">
      {PERIODOS.map((p) => (
        <button
          key={p.dias}
          type="button"
          role="radio"
          aria-checked={p.dias === dias}
          onClick={() => onChange(p.dias)}
          className={cn(
            'rounded-md px-3 py-1 text-sm font-medium text-muted-foreground transition-colors outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring',
            p.dias === dias && 'bg-background text-foreground shadow-sm dark:bg-input/40',
          )}
        >
          {p.rotulo}
        </button>
      ))}
    </div>
  )
}

function Kpis({ p, hoje }: { p: ErrosPainel; hoje: string }) {
  const blocos = ROTULO_BLOCO.filter(([b]) => p.por_bloco[b]).map(([b, r]) => `${p.por_bloco[b]} ${r}`)
  const topo = p.por_categoria[0]
  const empatadas = topo ? p.por_categoria.filter((c) => c.n === topo.n).length : 0
  const doGrupo = topo ? p.por_categoria.filter((c) => c.grupo === topo.grupo).reduce((s, c) => s + c.n, 0) : 0
  const maisAntigo = p.padroes.abertos.reduce<ErrosPainel['padroes']['abertos'][number] | null>(
    (a, x) => (!a || x.aberto_em < a.aberto_em ? x : a),
    null,
  )
  return (
    // no celular: os dois números lado a lado e a categoria (texto comprido) embaixo, inteira
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <Kpi rotulo="Erros no período" valor={inteiro(p.total)} sub={p.total ? blocos.join(' · ') : 'nenhum registrado'} />
      <Kpi
        className="order-last col-span-2 sm:order-none sm:col-span-1"
        rotulo="Categoria mais frequente"
        valor={topo ? <span className="font-mono text-xl">{topo.categoria}</span> : '—'}
        sub={
          !topo
            ? 'sem erros no período'
            : empatadas > 1
              ? `${plural(topo.n, 'erro', 'erros')}, empatada com mais ${empatadas - 1}`
              : `${plural(topo.n, 'erro', 'erros')} · o grupo ${topo.grupo} soma ${doGrupo} de ${p.total} (${pctDeFracao(doGrupo / p.total)})`
        }
      />
      <Kpi
        rotulo="Padrões abertos"
        valor={inteiro(p.padroes.abertos.length)}
        sub={
          <>
            {plural(p.padroes.resolvidos.length, 'resolvido', 'resolvidos')}
            {maisAntigo && (
              <>
                {' · '}o mais antigo é <span className="font-mono">{maisAntigo.categoria}</span>, há {plural(diasEntre(maisAntigo.aberto_em, hoje), 'dia', 'dias')}
              </>
            )}
          </>
        }
      />
    </div>
  )
}

export function PaginaErros() {
  const [params, setParams] = useSearchParams()
  const pedido = Number(params.get('dias'))
  const dias = PERIODOS.some((p) => p.dias === pedido) ? pedido : PADRAO
  const filtro = params.get('categoria') ?? ''
  const hoje = paraIso(diaDeEstudoLocal())
  const q = useErrosPainel(dias)

  // período e filtro moram na URL: voltar, recarregar e mandar o link mantêm a vista
  const mudar = (patch: { dias?: number; categoria?: string }) =>
    setParams(
      (atual) => {
        const p = new URLSearchParams(atual)
        if (patch.dias !== undefined) p.set('dias', String(patch.dias))
        if (patch.categoria !== undefined) {
          if (patch.categoria) p.set('categoria', patch.categoria)
          else p.delete('categoria')
        }
        return p
      },
      { replace: true },
    )
  const filtrar = (categoria: string) => mudar({ categoria })
  // dos padrões (longe da lista, no celular) o filtro também leva até ela
  const filtrarEIr = (categoria: string) => {
    filtrar(categoria)
    document.getElementById('lista-erros')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (q.isError) return <ErroCarga erro={q.error} tentar={() => q.refetch()} />

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Erros</h1>
          <p className="text-sm text-muted-foreground">
            Os erros corrigidos nas aulas{q.data ? `, desde ${dataTabela(q.data.desde)}` : ''}.
          </p>
        </div>
        <SeletorPeriodo dias={dias} onChange={(d) => mudar({ dias: d })} />
      </header>

      {q.isPending ? (
        <EsqueletoErros />
      ) : (
        <>
          <Kpis p={q.data} hoje={hoje} />

          {/* Duas colunas independentes no computador (sem buraco quando um card
              é mais alto que o vizinho); no celular as colunas somem (contents) e
              a ordem põe a tabela de categorias, que filtra, ANTES da lista. */}
          <div className="flex flex-col gap-6 lg:grid lg:grid-cols-5 lg:items-start">
            <div className="contents lg:col-span-3 lg:flex lg:min-w-0 lg:flex-col lg:gap-6">
              <div className="order-1 min-w-0">
                <ErrosPorSemana painel={q.data} dias={dias} hoje={hoje} atualizando={q.isPlaceholderData} />
              </div>
              <div className="order-3 min-w-0">
                <ListaErros dias={dias} filtro={filtro} onFiltrar={filtrar} hoje={hoje} />
              </div>
              <div className="order-6 min-w-0">
                <RegistroAntigo />
              </div>
            </div>
            <div className="contents lg:col-span-2 lg:flex lg:min-w-0 lg:flex-col lg:gap-6">
              <div className="order-2 min-w-0">
                <TabelaCategorias porCategoria={q.data.por_categoria} filtro={filtro} onFiltrar={filtrar} hoje={hoje} atualizando={q.isPlaceholderData} />
              </div>
              <div className="order-4 min-w-0">
                <Padroes
                  padroes={q.data.padroes}
                  porCategoria={q.data.por_categoria}
                  dias={dias}
                  desde={q.data.desde}
                  primeiroErro={q.data.primeiro_erro}
                  hoje={hoje}
                  onFiltrar={filtrarEIr}
                />
              </div>
              <div className="order-5 min-w-0">
                <TiposExercicio tipos={q.data.tipos_exercicio} dias={dias} />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function EsqueletoErros() {
  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-3">
        {Array.from({ length: 3 }, (_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-5">
        <Skeleton className="h-80 rounded-xl lg:col-span-3" />
        <Skeleton className="h-80 rounded-xl lg:col-span-2" />
      </div>
      <Skeleton className="h-96 rounded-xl" />
    </div>
  )
}
