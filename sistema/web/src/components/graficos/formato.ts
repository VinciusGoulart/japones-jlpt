// Números no formato brasileiro, num lugar só: os gráficos, as dicas e as tabelas
// têm de mostrar o mesmo "84,9%" para o mesmo dado.
import './graficos.css'

const fmtInt = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })
const fmt1 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })
const fmtCompacto = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })

/** 1.284 */
export const inteiro = (n: number) => fmtInt.format(n)
/** 84,9 (sem casa decimal quando ela é zero: 100, não 100,0) */
export const decimal = (n: number) => fmt1.format(n)
/** 84,9% */
export const pct = (n: number) => `${fmt1.format(n)}%`
/** 0,25 → 25% */
export const pctDeFracao = (f: number) => `${fmtInt.format(f * 100)}%`
/** 1,2 mil — para os ticks do eixo, que não podem crescer com o número */
export const compacto = (n: number) => (Math.abs(n) < 1000 ? fmtInt.format(n) : fmtCompacto.format(n))

/** "1 erro" / "11 erros" — o plural sem gambiarra de "(s)" */
export function plural(n: number, um: string, varios: string): string {
  return `${inteiro(n)} ${n === 1 ? um : varios}`
}

/** "64 min", "1 h 05 min" */
export function minutos(m: number): string {
  const total = Math.round(m)
  if (total < 60) return `${total} min`
  const h = Math.floor(total / 60)
  const r = total % 60
  return r ? `${h} h ${String(r).padStart(2, '0')} min` : `${h} h`
}

/** Cores categóricas, na ordem fixa validada (ver graficos.css). Nunca reordenar nem ciclar. */
export const SERIES = ['var(--viz-s1)', 'var(--viz-s2)', 'var(--viz-s3)', 'var(--viz-s4)', 'var(--viz-s5)'] as const
export const COR_OUTROS = 'var(--viz-outros)'

/** Os acessórios dos eixos do Recharts: recessivos, na tinta de texto, nunca na cor da série. */
export const TICK = { fill: 'var(--muted-foreground)', fontSize: 11 } as const
export const GRADE = 'var(--border)'
