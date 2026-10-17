import { useEffect, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'
import { CalendarDays, Database } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { CaixaDica } from '@/components/graficos/CaixaDica'
import { CartaoGrafico } from '@/components/graficos/CartaoGrafico'
import { inteiro, minutos as fmtMin, plural } from '@/components/graficos/formato'
import { useLargura } from '@/components/graficos/useLargura'
import type { DiaAnki } from '@/api/types'
import { dataCurta, dataTabela, ddmm, diasEntre, paraData, paraIso, somarDias } from '@/lib/datas'
import { cn } from '@/lib/utils'

// Faixas fixas de 50 em 50 (não quantis): o mesmo dia tem a mesma cor hoje e
// daqui a um ano, e "100 cartões" continua sendo o mesmo tom quando a média subir.
const FAIXAS = ['nenhum', '1–49', '50–99', '100–149', '150–199', '200 ou mais'] as const
const nivel = (c: number) => (c <= 0 ? 0 : c < 50 ? 1 : c < 100 ? 2 : c < 150 ? 3 : c < 200 ? 4 : 5)

const AUDIO = { 1: 'ouviu', 0: 'não ouviu', nulo: 'não informado' } as const
const textoAudio = (a: DiaAnki['audio']) => (a === null ? AUDIO.nulo : AUDIO[a])

const ROTULO = 30 // coluna dos dias da semana
const TOPO = 16 // linha dos meses
const VAO = 3 // o fundo entre as células
const CEL_MIN = 11
const CEL_MAX = 26
const MESES = new Intl.DateTimeFormat('pt-BR', { month: 'short' })
const DIAS_SEMANA = ['seg', '', 'qua', '', 'sex', '', ''] as const

interface Celula {
  i: number
  dia: DiaAnki
  semana: number
  linha: number
}

function MarcaAudio({ audio, cx, cy, cel }: { audio: DiaAnki['audio']; cx: number; cy: number; cel: number }) {
  // ouviu = ponto; não ouviu = ×; não informado = sem marca. Forma, não cor:
  // separa também para daltônico e no P&B. (Um anel vazio para "não ouviu" foi
  // testado e se confundia com o ponto em célula pequena.) As duas marcas usam
  // tinta escura com halo claro, que lê sobre qualquer degrau da rampa.
  if (audio === 1)
    return <circle cx={cx} cy={cy} r={Math.max(2.25, cel * 0.15)} fill="var(--viz-marca-tinta)" stroke="var(--viz-marca-halo)" strokeWidth={1.25} pointerEvents="none" />
  if (audio === 0) {
    const b = Math.max(2.5, cel * 0.18)
    const d = `M${cx - b},${cy - b} L${cx + b},${cy + b} M${cx + b},${cy - b} L${cx - b},${cy + b}`
    return (
      <g pointerEvents="none" fill="none" strokeLinecap="round">
        <path d={d} stroke="var(--viz-marca-halo)" strokeWidth={4} />
        <path d={d} stroke="var(--viz-marca-tinta)" strokeWidth={1.75} />
      </g>
    )
  }
  return null
}

export function MapaCalor({ dias, fonte }: { dias: DiaAnki[]; fonte?: string }) {
  const [ref, largura] = useLargura<HTMLDivElement>()
  const rolagem = useRef<HTMLDivElement>(null)
  const [ativo, setAtivo] = useState<{ i: number; x: number; y: number } | null>(null)

  // a última linha do por_dia é o dia de estudo de hoje (o servidor manda até hoje, sem buraco)
  const hoje = dias[dias.length - 1]?.data ?? ''
  const celulas = useMemo<Celula[]>(() => {
    if (!dias.length) return []
    const d0 = paraData(dias[0].data)
    // colunas de semana começando na segunda (getDay: 0 = domingo)
    const segunda0 = paraIso(somarDias(d0, -((d0.getDay() + 6) % 7)))
    return dias.map((dia, i) => {
      const n = diasEntre(segunda0, dia.data)
      return { i, dia, semana: Math.floor(n / 7), linha: n % 7 }
    })
  }, [dias])
  const nSemanas = celulas.length ? celulas[celulas.length - 1].semana + 1 : 0

  // célula do tamanho que couber, entre o mínimo legível e o máximo que ainda parece mapa
  const passo = largura ? Math.min(CEL_MAX + VAO, Math.max(CEL_MIN + VAO, Math.floor((largura - ROTULO) / Math.max(nSemanas, 1)))) : CEL_MAX + VAO
  const cel = passo - VAO
  const larguraSvg = ROTULO + nSemanas * passo
  const alturaSvg = TOPO + 7 * passo

  // com mais semanas do que cabem, o mapa rola por dentro e abre no fim (o recente)
  useLayoutEffect(() => {
    const el = rolagem.current
    if (el) el.scrollLeft = el.scrollWidth
  }, [larguraSvg])

  // a dica é fixa na janela: some se a página rolar, em vez de ficar solta
  useEffect(() => {
    if (!ativo) return
    const sumir = () => setAtivo(null)
    window.addEventListener('scroll', sumir, { passive: true })
    return () => window.removeEventListener('scroll', sumir)
  }, [ativo])

  const meses = useMemo(() => {
    const r: { x: number; rotulo: string }[] = []
    let anterior = -1
    for (let s = 0; s < nSemanas; s++) {
      const c = celulas.find((x) => x.semana === s)
      if (!c) continue
      const m = paraData(c.dia.data).getMonth()
      if (m !== anterior) r.push({ x: ROTULO + s * passo, rotulo: MESES.format(paraData(c.dia.data)).replace('.', '') })
      anterior = m
    }
    return r
  }, [celulas, nSemanas, passo])

  const resumo = useMemo(() => {
    const passados = dias.filter((d) => d.data < hoje) // hoje ainda não acabou: fica fora das médias
    const comRevisao = passados.filter((d) => d.cartoes > 0).length
    const total = passados.reduce((s, d) => s + d.cartoes, 0)
    const mins = dias.reduce((s, d) => s + d.minutos, 0)
    const maior = dias.reduce<DiaAnki | null>((m, d) => (!m || d.cartoes > m.cartoes ? d : m), null)
    const audio = { 1: 0, 0: 0, nulo: 0 }
    for (const d of passados) audio[d.audio === null ? 'nulo' : d.audio]++
    return { passados: passados.length, comRevisao, media: passados.length ? total / passados.length : 0, mins, maior, audio }
  }, [dias, hoje])

  const mostrar = (i: number) => {
    const svg = rolagem.current?.querySelector('svg')
    const c = celulas[i]
    if (!svg || !c) return
    const r = svg.getBoundingClientRect()
    const meio = 132 // metade da largura máxima da dica: não deixa ela sair da tela no celular
    const x = Math.min(window.innerWidth - meio, Math.max(meio, r.left + ROTULO + c.semana * passo + cel / 2))
    setAtivo({ i, x, y: r.top + TOPO + c.linha * passo })
  }

  const teclado = (e: KeyboardEvent) => {
    const atual = ativo?.i ?? celulas.length - 1
    const salto = { ArrowLeft: -7, ArrowRight: 7, ArrowUp: -1, ArrowDown: 1, Home: -atual, End: celulas.length - 1 - atual }[e.key]
    if (salto === undefined) return
    e.preventDefault()
    mostrar(Math.min(celulas.length - 1, Math.max(0, atual + salto)))
  }

  const ativa = ativo ? celulas[ativo.i] : null

  const tabela = (
    <div className="max-h-96 overflow-y-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Dia</TableHead>
            <TableHead className="text-right">Cartões</TableHead>
            <TableHead className="text-right">Minutos</TableHead>
            <TableHead>Áudio</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {[...dias].reverse().map((d) => (
            <TableRow key={d.data}>
              <TableCell className="tabular-nums">
                {dataTabela(d.data)}
                {d.data === hoje && <span className="ml-1 text-xs text-muted-foreground">hoje</span>}
              </TableCell>
              <TableCell className="text-right tabular-nums">{inteiro(d.cartoes)}</TableCell>
              <TableCell className="text-right tabular-nums">{Math.round(d.minutos)}</TableCell>
              <TableCell className={cn(d.audio === null && 'text-muted-foreground')}>{textoAudio(d.audio)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )

  return (
    <CartaoGrafico
      titulo={`Cartões por dia desde ${dias[0] ? ddmm(dias[0].data) : '03/08'}`}
      icone={<CalendarDays />}
      descricao="Cada quadrado é um dia de estudo (vira às 04:00), em colunas de semana começando na segunda. A cor é o número de cartões revisados; a marca dentro é o áudio do trajeto."
      tabela={tabela}
    >
      <div className="space-y-4">
        {fonte && (
          <p className="flex items-start gap-2 rounded-md bg-aviso-bg px-3 py-2 text-sm text-aviso">
            <Database className="mt-0.5 size-4 shrink-0" />
            <span>
              Fonte do mapa: {fonte}. São os números que o trajeto registrou dia a dia; dia sem registro aparece como zero, e o de hoje pode
              estar incompleto.
            </span>
          </p>
        )}
        {/* mede a LINHA inteira: o mapa ocupa só a largura das semanas que tem, e o
            resumo pega o resto; quando as semanas enchem a linha, o resumo desce */}
        <div ref={ref} className="flex flex-wrap items-start gap-x-10 gap-y-4">
          <div className="max-w-full min-w-0 flex-none">
            <div
              ref={rolagem}
              tabIndex={0}
              role="group"
              aria-label={`Mapa de calor de ${dias.length} dias. Use as setas para percorrer os dias.`}
              onKeyDown={teclado}
              onFocus={() => !ativo && mostrar(celulas.length - 1)}
              onBlur={() => setAtivo(null)}
              onPointerLeave={(e: PointerEvent) => e.pointerType === 'mouse' && setAtivo(null)}
              className="overflow-x-auto rounded-md pb-1 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <svg width={larguraSvg} height={alturaSvg} className="block" aria-hidden>
                {meses.map((m) => (
                  <text key={m.x} x={m.x} y={11} fontSize={11} fill="var(--muted-foreground)">
                    {m.rotulo}
                  </text>
                ))}
                {DIAS_SEMANA.map((d, l) =>
                  d ? (
                    <text key={d} x={0} y={TOPO + l * passo + cel / 2 + 4} fontSize={11} fill="var(--muted-foreground)">
                      {d}
                    </text>
                  ) : null,
                )}
                {celulas.map((c) => {
                  const x = ROTULO + c.semana * passo
                  const y = TOPO + c.linha * passo
                  const n = nivel(c.dia.cartoes)
                  const eHoje = c.dia.data === hoje
                  return (
                    <g key={c.dia.data} onPointerEnter={() => mostrar(c.i)} onClick={() => mostrar(c.i)}>
                      <rect
                        x={x}
                        y={y}
                        width={cel}
                        height={cel}
                        rx={3}
                        fill={`var(--viz-seq-${n})`}
                        className={cn(ativo?.i === c.i && 'brightness-110')}
                      />
                      {/* hoje: contorno na cor de ação, porque o zero de hoje ainda não é falta */}
                      {eHoje && <rect x={x + 1} y={y + 1} width={cel - 2} height={cel - 2} rx={2.5} fill="none" stroke="var(--primary)" strokeWidth={2} />}
                      {ativo?.i === c.i && !eHoje && (
                        <rect x={x + 0.75} y={y + 0.75} width={cel - 1.5} height={cel - 1.5} rx={2.5} fill="none" stroke="var(--foreground)" strokeWidth={1.5} />
                      )}
                      <MarcaAudio audio={c.dia.audio} cx={x + cel / 2} cy={y + cel / 2} cel={cel} />
                    </g>
                  )
                })}
              </svg>
            </div>
          </div>

          <dl className="grid min-w-64 flex-1 grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">Dias com revisão</dt>
              <dd className="font-medium">
                {resumo.comRevisao} de {resumo.passados}
                <span className="text-xs font-normal text-muted-foreground"> (sem contar hoje)</span>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Média por dia</dt>
              <dd className="font-medium">{plural(Math.round(resumo.media), 'cartão', 'cartões')}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Tempo no Anki</dt>
              <dd className="font-medium">{fmtMin(resumo.mins)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Maior dia</dt>
              <dd className="font-medium">{resumo.maior ? `${inteiro(resumo.maior.cartoes)} (${ddmm(resumo.maior.data)})` : '—'}</dd>
            </div>
            <div className="col-span-2">
              <dt className="text-xs text-muted-foreground">Áudio no trajeto</dt>
              <dd className="font-medium">
                {resumo.audio[1]} ouviu · {resumo.audio[0]} não ouviu ·{' '}
                <span className={cn(resumo.audio.nulo > 0 && 'text-muted-foreground')}>{resumo.audio.nulo} sem registro</span>
              </dd>
            </div>
          </dl>
        </div>

        {/* legenda: a escala da cor e as três marcas de áudio */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
          <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
            <span>Cartões:</span>
            {FAIXAS.map((f, n) => (
              <span key={f} className="flex items-center gap-1">
                <span className="inline-block size-3 rounded-[3px]" style={{ background: `var(--viz-seq-${n})` }} />
                <span className="mr-1">{n === 0 ? '0' : f}</span>
              </span>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>Áudio:</span>
            <span className="flex items-center gap-1 whitespace-nowrap">
              <svg width="14" height="14" aria-hidden>
                <rect width="14" height="14" rx="3" fill="var(--viz-seq-0)" />
                <circle cx="7" cy="7" r="2.5" fill="var(--viz-marca-tinta)" stroke="var(--viz-marca-halo)" strokeWidth="1.25" />
              </svg>
              ouviu
            </span>
            <span className="flex items-center gap-1 whitespace-nowrap">
              <svg width="14" height="14" aria-hidden>
                <rect width="14" height="14" rx="3" fill="var(--viz-seq-0)" />
                <path d="M4.5,4.5 L9.5,9.5 M9.5,4.5 L4.5,9.5" fill="none" strokeLinecap="round" stroke="var(--viz-marca-halo)" strokeWidth="4" />
                <path d="M4.5,4.5 L9.5,9.5 M9.5,4.5 L4.5,9.5" fill="none" strokeLinecap="round" stroke="var(--viz-marca-tinta)" strokeWidth="1.75" />
              </svg>
              não ouviu
            </span>
            <span className="flex items-center gap-1 whitespace-nowrap">
              <svg width="14" height="14" aria-hidden>
                <rect width="14" height="14" rx="3" fill="var(--viz-seq-0)" />
              </svg>
              sem marca: não informado
            </span>
          </div>
          <span className="flex items-center gap-1 whitespace-nowrap">
            <svg width="14" height="14" aria-hidden>
              <rect x="1" y="1" width="12" height="12" rx="2.5" fill="var(--viz-seq-0)" stroke="var(--primary)" strokeWidth="2" />
            </svg>
            hoje (em andamento)
          </span>
        </div>

        {ativa && ativo && (
          <div className="fixed z-50" style={{ left: ativo.x, top: ativo.y, transform: 'translate(-50%, calc(-100% - 8px))' }}>
            <CaixaDica
              titulo={
                <span className="first-letter:uppercase">
                  {dataCurta(ativa.dia.data)}
                  {ativa.dia.data === hoje && ' · hoje, em andamento'}
                </span>
              }
              linhas={[
                { chave: 'c', valor: inteiro(ativa.dia.cartoes), rotulo: ativa.dia.cartoes === 1 ? 'cartão' : 'cartões' },
                { chave: 'm', valor: fmtMin(ativa.dia.minutos), rotulo: 'no Anki' },
                { chave: 'a', valor: textoAudio(ativa.dia.audio), rotulo: 'áudio' },
              ]}
            />
          </div>
        )}
      </div>
    </CartaoGrafico>
  )
}
