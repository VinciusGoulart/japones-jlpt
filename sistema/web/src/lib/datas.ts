// Datas da API são o DIA DE ESTUDO em 'AAAA-MM-DD' (vira às 04:00, DESIGN §5).
// Nunca passar essas strings por new Date('AAAA-MM-DD'): isso é meia-noite UTC,
// que no Brasil cai no dia anterior.

const DIA_MS = 86_400_000
/** mesma regra do dominio.dia_de_estudo no Python */
const VIRADA_H = 4

export function paraData(iso: string): Date {
  const [a, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(a, m - 1, d)
}

export function paraIso(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

export function somarDias(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n)
}

/** O dia de estudo de agora, pelo relógio do navegador. */
export function diaDeEstudoLocal(agora = new Date()): Date {
  const d = new Date(agora.getTime() - VIRADA_H * 3_600_000)
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

export function diasEntre(de: string, ate: string): number {
  return Math.round((paraData(ate).getTime() - paraData(de).getTime()) / DIA_MS)
}

/** "hoje", "amanhã", "em 3 dias", "ontem", "há 2 dias" — relativo ao dia de estudo `hoje`. */
export function relativo(data: string, hoje: string): string {
  const n = diasEntre(hoje, data)
  if (n === 0) return 'hoje'
  if (n === 1) return 'amanhã'
  if (n === -1) return 'ontem'
  return n > 0 ? `em ${n} dias` : `há ${-n} dias`
}

const fmtCurta = new Intl.DateTimeFormat('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit' })
const fmtLonga = new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })
const fmtCompleta = new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
const fmtDdMm = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit' })
const fmtTabela = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })

/** "sáb., 17/10" */
export const dataCurta = (iso: string) => fmtCurta.format(paraData(iso))
/** "sábado, 17 de outubro" */
export const dataLonga = (iso: string) => fmtLonga.format(paraData(iso))
/** "sábado, 17 de outubro de 2026" */
export const dataCompleta = (iso: string) => fmtCompleta.format(paraData(iso))
/** "17/10" */
export const ddmm = (iso: string) => fmtDdMm.format(paraData(iso))
/** "17/10/2026" */
export const dataTabela = (iso: string) => fmtTabela.format(paraData(iso))
/** "sáb" */
export const diaDaSemana = (iso: string) =>
  new Intl.DateTimeFormat('pt-BR', { weekday: 'short' }).format(paraData(iso)).replace('.', '')
