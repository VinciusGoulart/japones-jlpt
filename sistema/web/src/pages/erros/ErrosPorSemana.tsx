import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, type BarShapeProps, type TooltipContentProps } from 'recharts'
import { ChartColumn } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Vazio } from '@/components/Estados'
import { BarraEmpilhada } from '@/components/graficos/BarraEmpilhada'
import { CaixaDica } from '@/components/graficos/CaixaDica'
import { CartaoGrafico } from '@/components/graficos/CartaoGrafico'
import { Legenda } from '@/components/graficos/Legenda'
import { GRADE, TICK, inteiro, plural } from '@/components/graficos/formato'
import type { ErrosPainel } from '@/api/types'
import { ddmm, paraData, paraIso, somarDias } from '@/lib/datas'
import { FAMILIAS, familiaDe, type IdFamilia } from './familias'

interface LinhaSemana extends Partial<Record<IdFamilia, number>> {
  semana: string
  rotulo: string
  total: number
  /** os grupos de cada família naquela semana, para a dica */
  grupos: Partial<Record<IdFamilia, { grupo: string; n: number }[]>>
}

/** A segunda-feira da semana de um dia (a mesma regra do painel.py). */
function segunda(iso: string): string {
  const d = paraData(iso)
  return paraIso(somarDias(d, -((d.getDay() + 6) % 7)))
}

function montar(porSemana: ErrosPainel['por_semana'], hoje: string) {
  const mapa = new Map<string, LinhaSemana>()
  const linha = (semana: string) => {
    let l = mapa.get(semana)
    if (!l) mapa.set(semana, (l = { semana, rotulo: ddmm(semana), total: 0, grupos: {} }))
    return l
  }
  for (const { semana, grupo, n } of porSemana) {
    const f = familiaDe(grupo).id
    const l = linha(semana)
    l[f] = (l[f] ?? 0) + n
    l.total += n
    ;(l.grupos[f] ??= []).push({ grupo, n })
  }
  if (mapa.size === 0) return []
  // do primeiro registro até a semana de hoje, com as semanas sem erro em zero:
  // um buraco no eixo esconderia justamente as semanas limpas
  const chaves = [...mapa.keys()].sort()
  const primeira = chaves[0]
  // até a semana de hoje, ou a última com dado se o relógio do navegador estiver atrasado
  const ultima = [segunda(hoje), chaves[chaves.length - 1]].sort()[1]
  const linhas: LinhaSemana[] = []
  for (let s = primeira; s <= ultima; s = paraIso(somarDias(paraData(s), 7))) linhas.push(linha(s))
  return linhas
}

/**
 * Cada segmento da pilha: 2 px de vão acima do vizinho de baixo, e só o topo da
 * pilha arredondado (4 px), com o total da semana em cima. Desenhado à mão
 * porque o `radius` do Recharts arredonda TODO segmento, e o topo muda de
 * família de semana para semana.
 */
function criarSegmento(id: IdFamilia, ordem: IdFamilia[], semanaAtual: string) {
  return function Segmento({ x, y, width, height, fill, payload }: BarShapeProps) {
    const l = payload as LinhaSemana
    if (!height || height <= 0) return <g />
    const presentes = ordem.filter((k) => (l[k] ?? 0) > 0)
    const topo = presentes[presentes.length - 1] === id
    const base = presentes[0] === id
    const h = base ? height : Math.max(0, height - 2)
    const r = topo ? Math.min(4, width / 2, h) : 0
    const d = `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${y + h} Z`
    return (
      <g>
        <path d={d} fill={fill} />
        {topo && (
          <text x={x + width / 2} y={y - 6} textAnchor="middle" fontSize={11} fontWeight={600} fill="var(--foreground)">
            {l.total}
            {l.semana === semanaAtual ? '*' : ''}
          </text>
        )}
      </g>
    )
  }
}

function Dica({ active, payload, semanaAtual }: Pick<TooltipContentProps, 'active' | 'payload'> & { semanaAtual: string }) {
  const l = payload?.[0]?.payload as LinhaSemana | undefined
  if (!active || !l) return null
  // de cima para baixo, na ordem em que a pilha aparece
  const linhas = [...FAMILIAS].reverse().flatMap((f) => {
    const n = l[f.id] ?? 0
    if (!n) return []
    const grupos = l.grupos[f.id] ?? []
    const detalhe = grupos.length > 1 || (grupos[0] && grupos[0].grupo !== f.id) ? grupos.map((g) => `${g.grupo} ${g.n}`).join(' · ') : undefined
    return [{ chave: f.id, valor: n, rotulo: f.rotulo, cor: f.cor, detalhe }]
  })
  return (
    <CaixaDica
      titulo={`Semana de ${l.rotulo}${l.semana === semanaAtual ? ' (em andamento)' : ''}`}
      linhas={linhas.length ? linhas : [{ chave: 'zero', valor: 0, rotulo: 'erros registrados' }]}
      rodape={linhas.length > 1 ? `${plural(l.total, 'erro', 'erros')} na semana` : undefined}
    />
  )
}

export function ErrosPorSemana({ painel, dias, hoje, atualizando }: { painel: ErrosPainel; dias: number; hoje: string; atualizando: boolean }) {
  const linhas = useMemo(() => montar(painel.por_semana, hoje), [painel.por_semana, hoje])
  const semanaAtual = segunda(hoje)
  const totais = useMemo(() => {
    const t = new Map<IdFamilia, number>()
    for (const l of linhas) for (const f of FAMILIAS) t.set(f.id, (t.get(f.id) ?? 0) + (l[f.id] ?? 0))
    return t
  }, [linhas])
  // só as famílias com erro no período entram na pilha e na legenda; a cor de cada uma não muda
  const presentes = FAMILIAS.filter((f) => (totais.get(f.id) ?? 0) > 0)
  const ordem = presentes.map((f) => f.id)
  const legenda = presentes.map((f) => ({ chave: f.id, rotulo: f.rotulo, cor: f.cor, valor: inteiro(totais.get(f.id) ?? 0) }))

  const tabela = (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Semana</TableHead>
          {presentes.map((f) => (
            <TableHead key={f.id} className="text-right">
              {f.rotulo}
            </TableHead>
          ))}
          <TableHead className="text-right">Total</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {[...linhas].reverse().map((l) => (
          <TableRow key={l.semana}>
            <TableCell className="tabular-nums">
              {l.rotulo}
              {l.semana === semanaAtual && <span className="ml-1 text-xs text-muted-foreground">em andamento</span>}
            </TableCell>
            {presentes.map((f) => (
              <TableCell key={f.id} className="text-right tabular-nums">
                {l[f.id] ?? 0}
              </TableCell>
            ))}
            <TableCell className="text-right font-medium tabular-nums">{l.total}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )

  const titulo = 'Erros por semana'
  if (linhas.length === 0)
    return (
      <CartaoGrafico titulo={titulo} icone={<ChartColumn />} atualizando={atualizando}>
        <Vazio>
          Nenhum erro registrado nos últimos {dias} dias. Cada erro corrigido na aula entra aqui quando o tutor o registra (com a categoria), e as
          semanas aparecem empilhadas pela família do erro.
        </Vazio>
      </CartaoGrafico>
    )

  // Uma semana só: uma coluna solitária num eixo vazio não diz nada. Mostra a
  // composição daquela semana, que é o que o dado tem a dizer por enquanto.
  if (linhas.length === 1) {
    const l = linhas[0]
    return (
      <CartaoGrafico
        titulo={titulo}
        icone={<ChartColumn />}
        atualizando={atualizando}
        descricao={`Só há registro na semana de ${l.rotulo}${l.semana === semanaAtual ? ' (esta semana)' : ''}. A evolução semana a semana aparece a partir da segunda semana com erros registrados.`}
        tabela={tabela}
      >
        <div className="space-y-3">
          <p className="text-sm">
            <span className="text-2xl font-semibold">{l.total}</span>{' '}
            <span className="text-muted-foreground">{l.total === 1 ? 'erro' : 'erros'} na semana de {l.rotulo}, por família</span>
          </p>
          <BarraEmpilhada
            rotulo={`Erros da semana de ${l.rotulo} por família`}
            altura={18}
            partes={presentes.map((f) => ({
              chave: f.id,
              rotulo: f.rotulo,
              valor: l[f.id] ?? 0,
              cor: f.cor,
              dica: `${f.rotulo}: ${l[f.id] ?? 0} (${(l.grupos[f.id] ?? []).map((g) => `${g.grupo} ${g.n}`).join(', ')})`,
            }))}
          />
          <Legenda itens={legenda} />
        </div>
      </CartaoGrafico>
    )
  }

  return (
    <CartaoGrafico
      titulo={titulo}
      icone={<ChartColumn />}
      atualizando={atualizando}
      descricao={`Empilhado pela família da categoria, desde a primeira semana com registro no período (${linhas[0].rotulo}). A dica abre cada família nos grupos.`}
      tabela={tabela}
    >
      <div className="space-y-3">
        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={linhas} margin={{ top: 20, right: 4, bottom: 0, left: -8 }} barCategoryGap="30%">
              <CartesianGrid vertical={false} stroke={GRADE} />
              <XAxis dataKey="rotulo" tick={TICK} tickLine={false} axisLine={{ stroke: 'var(--border)' }} interval="preserveStartEnd" minTickGap={12} />
              <YAxis allowDecimals={false} tick={TICK} tickLine={false} axisLine={false} width={36} />
              <Tooltip
                cursor={{ fill: 'var(--muted)', opacity: 0.6 }}
                content={(p) => <Dica {...p} semanaAtual={semanaAtual} />}
                isAnimationActive={false}
              />
              {presentes.map((f) => (
                <Bar
                  key={f.id}
                  dataKey={f.id}
                  name={f.rotulo}
                  stackId="erros"
                  fill={f.cor}
                  maxBarSize={24}
                  isAnimationActive={false}
                  shape={criarSegmento(f.id, ordem, semanaAtual)}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <Legenda itens={legenda} />
        {linhas.some((l) => l.semana === semanaAtual && l.total > 0) && (
          <p className="text-[11px] text-muted-foreground">* semana em andamento</p>
        )}
      </div>
    </CartaoGrafico>
  )
}
