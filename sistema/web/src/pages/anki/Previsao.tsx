import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis, type LabelProps, type TooltipContentProps } from 'recharts'
import { CalendarClock } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Vazio } from '@/components/Estados'
import { CaixaDica } from '@/components/graficos/CaixaDica'
import { CartaoGrafico } from '@/components/graficos/CartaoGrafico'
import { GRADE, TICK, compacto, inteiro, plural } from '@/components/graficos/formato'
import type { GraficosAnki } from '@/api/types'
import { dataCurta, diaDaSemana, paraData } from '@/lib/datas'

type Dia = GraficosAnki['previsao'][number] & { dd: string; sem: string; hoje: boolean }

function Dica({ active, payload, atrasados }: Pick<TooltipContentProps, 'active' | 'payload'> & { atrasados: number | null }) {
  const d = payload?.[0]?.payload as Dia | undefined
  if (!active || !d) return null
  return (
    <CaixaDica
      titulo={<span className="first-letter:uppercase">{`${dataCurta(d.data)}${d.hoje ? ' · hoje' : ''}`}</span>}
      linhas={[{ chave: 'd', valor: inteiro(d.devidos), rotulo: 'revisões devidas', cor: 'var(--viz-s1)' }]}
      rodape={d.hoje ? (atrasados === null ? 'Inclui os atrasados.' : `Inclui ${plural(atrasados, 'atrasado', 'atrasados')}.`) : undefined}
    />
  )
}

/** Dois andares de rótulo no eixo: o dia do mês e, embaixo, o dia da semana ("hoje" no primeiro). */
function Tick({ x, y, index, dados }: { x?: number | string; y?: number | string; index?: number; dados: Dia[] }) {
  const d = index !== undefined ? dados[index] : undefined
  if (!d || x === undefined || y === undefined) return null
  return (
    <g transform={`translate(${Number(x)},${Number(y)})`}>
      <text y={10} textAnchor="middle" fontSize={11} fill="var(--muted-foreground)" fontWeight={d.hoje ? 600 : 400}>
        {d.dd}
      </text>
      <text y={23} textAnchor="middle" fontSize={10} fill="var(--muted-foreground)">
        {d.hoje ? 'hoje' : d.sem}
      </text>
    </g>
  )
}

/** Só o valor de hoje vai escrito na barra: os outros ficam no eixo, na dica e na tabela. */
function RotuloHoje({ x, y, width, value, index }: LabelProps) {
  if (index !== 0 || typeof x !== 'number' || typeof y !== 'number' || typeof width !== 'number') return null
  return (
    <text x={x + width / 2} y={y - 6} textAnchor="middle" fontSize={12} fontWeight={600} fill="var(--foreground)">
      {inteiro(Number(value))}
    </text>
  )
}

export function Previsao({ previsao, atrasados, hoje }: { previsao: GraficosAnki['previsao']; atrasados: number | null; hoje: string }) {
  const dados: Dia[] = previsao.map((p) => ({
    ...p,
    dd: String(paraData(p.data).getDate()),
    sem: diaDaSemana(p.data),
    hoje: p.data === hoje,
  }))
  const total = dados.reduce((s, d) => s + d.devidos, 0)
  const titulo = 'Previsão de 14 dias'
  if (dados.length === 0)
    return (
      <CartaoGrafico titulo={titulo} icone={<CalendarClock />}>
        <Vazio>Nada devido nos próximos 14 dias.</Vazio>
      </CartaoGrafico>
    )

  const tabela = (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Dia</TableHead>
          <TableHead className="text-right">Devidas</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {dados.map((d) => (
          <TableRow key={d.data}>
            <TableCell className="first-letter:uppercase">
              {dataCurta(d.data)}
              {d.hoje && <span className="ml-1 text-xs text-muted-foreground">hoje, com os atrasados</span>}
            </TableCell>
            <TableCell className="text-right tabular-nums">{inteiro(d.devidos)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )

  return (
    <CartaoGrafico
      titulo={titulo}
      icone={<CalendarClock />}
      descricao={`Revisões devidas por dia de estudo. A barra de hoje inclui os atrasados${atrasados ? ` (${inteiro(atrasados)})` : ''}.`}
      tabela={tabela}
    >
      <div className="space-y-3">
        <p className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-3xl font-semibold tracking-tight">{inteiro(total)}</span>
          <span className="text-sm text-muted-foreground">revisões em 14 dias · média de {inteiro(Math.round(total / dados.length))} por dia</span>
        </p>
        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={dados} margin={{ top: 20, right: 4, bottom: 0, left: -8 }} barCategoryGap="22%">
              <CartesianGrid vertical={false} stroke={GRADE} />
              <XAxis dataKey="data" tick={(p) => <Tick {...p} dados={dados} />} tickLine={false} axisLine={{ stroke: 'var(--border)' }} interval={0} height={32} />
              <YAxis allowDecimals={false} tick={TICK} tickFormatter={compacto} tickLine={false} axisLine={false} width={36} />
              <Tooltip cursor={{ fill: 'var(--muted)', opacity: 0.6 }} content={(p) => <Dica {...p} atrasados={atrasados} />} isAnimationActive={false} />
              <Bar dataKey="devidos" fill="var(--viz-s1)" radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false}>
                <LabelList dataKey="devidos" content={(p) => <RotuloHoje {...p} />} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </CartaoGrafico>
  )
}
