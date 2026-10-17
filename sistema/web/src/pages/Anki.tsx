import { CloudOff, TrendingDown } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga, FonteFora } from '@/components/Estados'
import { Kpi } from '@/components/graficos/Kpi'
import { inteiro, minutos, pct } from '@/components/graficos/formato'
import { Secao } from '@/pages/hoje/Secao'
import { useAnkiPainel } from '@/api/queries'
import { ehErro, type AnkiPainel, type DiaAnki, type GraficosAnki, type StatusAnki } from '@/api/types'
import { ddmm, diaDeEstudoLocal, paraData, paraIso, somarDias } from '@/lib/datas'
import { cn } from '@/lib/utils'
import { Baralhos } from './anki/Baralhos'
import { Listas } from './anki/Listas'
import { MapaCalor } from './anki/MapaCalor'
import { Botoes, Maturidade } from './anki/Maturidade'
import { Previsao } from './anki/Previsao'
import { RetencaoSemanal } from './anki/RetencaoSemanal'

/** "há 15 h": a idade da coleção lida. O que ele fez no celular depois do último sync ainda não está aqui. */
function idade(dias: number) {
  const h = dias * 24
  if (h < 1) return `há ${Math.max(1, Math.round(h * 60))} min`
  if (h < 48) return `há ${Math.round(h)} h`
  return `há ${Math.round(dias)} dias`
}

const segunda = (iso: string) => {
  const d = paraData(iso)
  return paraIso(somarDias(d, -((d.getDay() + 6) % 7)))
}

function Tiles({ dados, hoje }: { dados: AnkiPainel; hoje: DiaAnki | undefined }) {
  const ontem = dados.por_dia[dados.por_dia.length - 2]
  const status = ehErro(dados.status) ? null : dados.status
  const graficos = ehErro(dados.graficos) ? null : dados.graficos
  const ultimaSemana = graficos?.retencao_semanal[graficos.retencao_semanal.length - 1]
  const devidosHoje = graficos?.previsao[0]?.devidos
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Kpi
        rotulo="Hoje"
        valor={hoje ? inteiro(hoje.cartoes) : '—'}
        unidade="cartões"
        sub={hoje && (hoje.cartoes ? minutos(hoje.minutos) : 'nenhum ainda · o dia vai até as 04:00')}
      />
      <Kpi rotulo="Ontem" valor={ontem ? inteiro(ontem.cartoes) : '—'} unidade="cartões" sub={ontem && minutos(ontem.minutos)} />
      <Kpi
        rotulo="Fila de atrasados"
        valor={status ? inteiro(status.fila_atrasados) : '—'}
        sub={status ? (devidosHoje !== undefined ? `${inteiro(devidosHoje)} devidos hoje, contando os atrasados` : undefined) : 'Anki indisponível'}
        alerta={status?.alerta_fila}
      />
      <Kpi
        rotulo="Retenção em 30 dias"
        valor={status?.retencao_30d != null ? pct(status.retencao_30d) : '—'}
        sub={
          !status ? (
            'Anki indisponível'
          ) : ultimaSemana && status.retencao_30d != null ? (
            // a média de 30 dias esconde a queda: a última semana vai junto, sempre
            <span className={cn('flex items-center gap-1', ultimaSemana.pct < status.retencao_30d - 2 && 'font-medium text-aviso')}>
              {ultimaSemana.pct < status.retencao_30d - 2 && <TrendingDown className="size-3.5 shrink-0" />}
              semana de {ddmm(ultimaSemana.semana)}: {pct(ultimaSemana.pct)}
            </span>
          ) : status.retencao_30d == null ? (
            'sem revisões de cartão aprendido em 30 dias'
          ) : undefined
        }
        alerta={status?.alerta_retencao}
      />
    </div>
  )
}

function GraficosFora({ erro }: { erro: string }) {
  return (
    <Secao titulo="Retenção, previsão e maturidade" icone={<CloudOff />}>
      <FonteFora nome="Anki" erro={erro} />
    </Secao>
  )
}

function Graficos({ g, status, hoje }: { g: GraficosAnki; status: StatusAnki | null; hoje: string }) {
  return (
    <div className="grid items-start gap-6 lg:grid-cols-5">
      <div className="min-w-0 lg:col-span-3">
        <RetencaoSemanal semanas={g.retencao_semanal} semanaAtual={segunda(hoje)} />
      </div>
      <div className="min-w-0 lg:col-span-2">
        <Previsao previsao={g.previsao} atrasados={status ? status.fila_atrasados : null} hoje={hoje} />
      </div>
    </div>
  )
}

export function PaginaAnki() {
  const q = useAnkiPainel()
  if (q.isPending) return <EsqueletoAnki />
  if (q.isError) return <ErroCarga erro={q.error} tentar={() => q.refetch()} />
  const d = q.data
  const status = ehErro(d.status) ? null : d.status
  const hojeDia = d.por_dia[d.por_dia.length - 1]
  // o dia de estudo do servidor (a última linha do por_dia); o do navegador só se vier vazio
  const hoje = hojeDia?.data ?? paraIso(diaDeEstudoLocal())

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Anki</h1>
        {status ? (
          <p className="text-sm text-muted-foreground">
            Lido de {status.fonte.rotulo} · coleção salva{' '}
            <span className={cn(status.fonte.idade_dias > 1 && 'font-medium text-aviso')}>{idade(status.fonte.idade_dias)}</span>
          </p>
        ) : (
          ehErro(d.status) && <FonteFora nome="Anki" erro={d.status.erro} className="mt-2" />
        )}
      </header>

      <Tiles dados={d} hoje={hojeDia} />

      <MapaCalor dias={d.por_dia} fonte={d.fonte_por_dia} />

      {ehErro(d.graficos) ? <GraficosFora erro={d.graficos.erro} /> : <Graficos g={d.graficos} status={status} hoje={hoje} />}

      {(status || !ehErro(d.graficos)) && (
        <div className="grid items-start gap-6 lg:grid-cols-5">
          {!ehErro(d.graficos) && (
            <div className={cn('min-w-0', status ? 'lg:col-span-3' : 'lg:col-span-5')}>
              <Maturidade maturidade={d.graficos.maturidade} />
            </div>
          )}
          {status && (
            <div className={cn('min-w-0', ehErro(d.graficos) ? 'lg:col-span-5' : 'lg:col-span-2')}>
              <Botoes botoes={status.botoes_30d_pct} />
            </div>
          )}
        </div>
      )}

      {status ? (
        <>
          <Listas status={status} />
          <Baralhos baralhos={status.baralhos} />
        </>
      ) : (
        // um aviso só para tudo que depende do anki() (não um por card)
        <Secao titulo="Botões, em loop, travam, bandeira e baralhos" icone={<CloudOff />}>
          <FonteFora nome="Anki" erro={ehErro(d.status) ? d.status.erro : ''} />
        </Secao>
      )}
    </div>
  )
}

function EsqueletoAnki() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl" />
      <div className="grid gap-6 lg:grid-cols-5">
        <Skeleton className="h-80 rounded-xl lg:col-span-3" />
        <Skeleton className="h-80 rounded-xl lg:col-span-2" />
      </div>
    </div>
  )
}
