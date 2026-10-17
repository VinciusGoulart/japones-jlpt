import { CartesianGrid, LabelList, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, type LabelProps, type TooltipContentProps } from 'recharts'
import { ChartLine, TrendingDown } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Vazio } from '@/components/Estados'
import { CaixaDica } from '@/components/graficos/CaixaDica'
import { CartaoGrafico } from '@/components/graficos/CartaoGrafico'
import { GRADE, TICK, inteiro, pct, plural } from '@/components/graficos/formato'
import type { GraficosAnki } from '@/api/types'
import { ddmm } from '@/lib/datas'
import { cn } from '@/lib/utils'

// As mesmas réguas do alerta_retencao (japones/fontes/anki.py): abaixo de 85%
// de retenção, reduzir os novos; acima de 95%, dá para subir.
const REDUZIR = 85
const SUBIR = 95

type Semana = GraficosAnki['retencao_semanal'][number] & { rotulo: string; atual: boolean }

function Dica({ active, payload }: Pick<TooltipContentProps, 'active' | 'payload'>) {
  const s = payload?.[0]?.payload as Semana | undefined
  if (!active || !s) return null
  return (
    <CaixaDica
      titulo={`Semana de ${s.rotulo}${s.atual ? ' (em andamento)' : ''}`}
      linhas={[
        { chave: 'p', valor: pct(s.pct), rotulo: 'de retenção', cor: 'var(--viz-s1)' },
        { chave: 'r', valor: `${inteiro(s.acertos)} de ${inteiro(s.revisoes)}`, rotulo: 'revisões sem Again' },
      ]}
      rodape={s.pct < REDUZIR ? 'Abaixo de 85%: reduzir os novos.' : s.pct > SUBIR ? 'Acima de 95%: dá para subir os novos.' : undefined}
    />
  )
}

/**
 * O que a linha diz, em texto: a última semana, há quantas semanas cai e há
 * quantas está abaixo da régua. Escrito a partir dos números, sem adjetivo: a
 * regra do projeto é nunca maquiar o progresso, e queda escondida em média de
 * 30 dias (84,9% em 17/10, com a última semana em 65%) é maquiagem também.
 */
function leitura(s: Semana[]) {
  const n = s.length
  const ult = s[n - 1]
  let quedas = 0
  while (quedas < n - 1 && s[n - 1 - quedas].pct < s[n - 2 - quedas].pct) quedas++
  let abaixo = 0
  while (abaixo < n && s[n - 1 - abaixo].pct < REDUZIR) abaixo++
  const menor = n >= 3 && s.every((x) => x.pct >= ult.pct)
  const frases: string[] = []
  if (quedas >= 2) {
    const de = s[n - 1 - quedas]
    frases.push(`Em queda há ${quedas} semanas seguidas: de ${pct(de.pct)} (${de.rotulo}) para ${pct(ult.pct)}.`)
  }
  if (abaixo > 0) frases.push(`Abaixo de 85% ${abaixo === 1 ? 'nesta semana' : `há ${abaixo} semanas`}: pelo método, é hora de reduzir os cartões novos.`)
  // o servidor manda as 12 últimas semanas: com menos que isso, a série começa no início do plano
  if (menor) frases.push(n < 12 ? 'É a mais baixa desde o início do plano.' : `É a mais baixa das últimas ${n} semanas.`)
  return { ult, frases, ruim: ult.pct < REDUZIR }
}

function RotuloFinal({ x, y, value, index, dados }: LabelProps & { dados: Semana[] }) {
  if (index !== dados.length - 1 || typeof x !== 'number' || typeof y !== 'number') return null
  // se a linha chega descendo, o rótulo vai embaixo do ponto (em cima, ele cairia sobre a linha)
  const desce = dados.length > 1 && dados[dados.length - 2].pct > dados[dados.length - 1].pct
  return (
    <text x={x - 6} y={desce ? y + 18 : y - 10} textAnchor="end" fontSize={12} fontWeight={600} fill="var(--foreground)">
      {pct(Number(value))}
    </text>
  )
}

export function RetencaoSemanal({ semanas, semanaAtual }: { semanas: GraficosAnki['retencao_semanal']; semanaAtual: string }) {
  const dados: Semana[] = semanas.map((s) => ({ ...s, rotulo: ddmm(s.semana), atual: s.semana === semanaAtual }))
  const titulo = 'Retenção por semana'
  if (dados.length === 0)
    return (
      <CartaoGrafico titulo={titulo} icone={<ChartLine />}>
        <Vazio>Nenhuma revisão de cartão já aprendido ainda.</Vazio>
      </CartaoGrafico>
    )

  const { ult, frases, ruim } = leitura(dados)
  // o eixo não começa no zero (é linha, não barra) mas sempre mostra a régua dos 85%
  const minimo = Math.min(...dados.map((d) => d.pct))
  const piso = Math.min(80, Math.floor((minimo - 5) / 10) * 10)
  const ticks = Array.from({ length: (100 - piso) / 10 + 1 }, (_, i) => piso + i * 10)

  const tabela = (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Semana</TableHead>
          <TableHead className="text-right">Revisões</TableHead>
          <TableHead className="text-right">Sem Again</TableHead>
          <TableHead className="text-right">Retenção</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {[...dados].reverse().map((s) => (
          <TableRow key={s.semana}>
            <TableCell className="tabular-nums">
              {s.rotulo}
              {s.atual && <span className="ml-1 text-xs text-muted-foreground">em andamento</span>}
            </TableCell>
            <TableCell className="text-right tabular-nums">{inteiro(s.revisoes)}</TableCell>
            <TableCell className="text-right tabular-nums">{inteiro(s.acertos)}</TableCell>
            <TableCell className={cn('text-right font-medium tabular-nums', s.pct < REDUZIR && 'text-aviso')}>{pct(s.pct)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )

  return (
    <CartaoGrafico
      titulo={titulo}
      icone={<ChartLine />}
      descricao="Revisões de cartões já aprendidos; conta como acerto qualquer botão menos Again. A faixa sombreada é a zona abaixo dos 85%."
      tabela={tabela}
    >
      <div className="space-y-3">
        <div className="space-y-1">
          <p className="flex flex-wrap items-baseline gap-x-2">
            <span className={cn('text-3xl font-semibold tracking-tight', ruim && 'text-aviso')}>{pct(ult.pct)}</span>
            <span className="text-sm text-muted-foreground">
              na semana de {ult.rotulo}
              {ult.atual ? ' (em andamento)' : ''} · {plural(ult.revisoes, 'revisão', 'revisões')}
            </span>
          </p>
          {frases.length > 0 && (
            <p className={cn('flex items-start gap-1.5 text-sm', ruim ? 'text-aviso' : 'text-muted-foreground')}>
              {ruim && <TrendingDown className="mt-0.5 size-4 shrink-0" />}
              <span>{frases.join(' ')}</span>
            </p>
          )}
        </div>
        <div className="h-60 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dados} margin={{ top: 22, right: 40, bottom: 0, left: -4 }}>
              <CartesianGrid vertical={false} stroke={GRADE} />
              <ReferenceArea y1={piso} y2={REDUZIR} fill="var(--aviso)" fillOpacity={0.09} stroke="none" ifOverflow="hidden" />
              <ReferenceLine
                y={REDUZIR}
                stroke="var(--aviso)"
                strokeWidth={1.5}
                label={{ value: '85%', position: 'right', fill: 'var(--aviso)', fontSize: 11, fontWeight: 600 }}
              />
              <ReferenceLine y={SUBIR} stroke="var(--muted-foreground)" strokeOpacity={0.5} label={{ value: '95%', position: 'right', fill: 'var(--muted-foreground)', fontSize: 11 }} />
              <XAxis dataKey="rotulo" tick={TICK} tickLine={false} axisLine={{ stroke: 'var(--border)' }} interval="preserveStartEnd" minTickGap={8} />
              <YAxis domain={[piso, 100]} ticks={ticks} tickFormatter={(v: number) => `${v}%`} tick={TICK} tickLine={false} axisLine={false} width={44} />
              <Tooltip cursor={{ stroke: 'var(--muted-foreground)', strokeWidth: 1 }} content={(p) => <Dica {...p} />} isAnimationActive={false} />
              <Line
                dataKey="pct"
                stroke="var(--viz-s1)"
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
                dot={{ r: 4, fill: 'var(--viz-s1)', stroke: 'var(--card)', strokeWidth: 2 }}
                activeDot={{ r: 5, fill: 'var(--viz-s1)', stroke: 'var(--card)', strokeWidth: 2 }}
                isAnimationActive={false}
              >
                <LabelList dataKey="pct" content={(p) => <RotuloFinal {...p} dados={dados} />} />
              </Line>
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-3 rounded-full bg-aviso" /> 85%: abaixo disso, reduzir novos
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-3 rounded-full bg-muted-foreground/60" /> 95%: acima disso, dá para subir novos
          </span>
        </p>
      </div>
    </CartaoGrafico>
  )
}
