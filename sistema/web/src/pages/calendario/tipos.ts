import type { DiaCalendario, TipoAula } from '@/api/types'

export const ROTULO_AULA: Record<TipoAula, string> = {
  completa: 'completa',
  parcial: 'parcial',
  sem_mesa: 'sem mesa',
}

export const CLASSE_AULA: Record<TipoAula, string> = {
  completa: 'bg-ok-bg text-ok',
  parcial: 'bg-aviso-bg text-aviso',
  sem_mesa: 'bg-erro-bg text-erro',
}

/** Dia com duas sessões (08/08, 14/09): a cor é a da melhor. */
export function tipoDoDia(d: DiaCalendario | undefined): TipoAula | null {
  if (!d?.aulas.length) return null
  const ordem: TipoAula[] = ['completa', 'parcial', 'sem_mesa']
  return ordem.find((t) => d.aulas.some((a) => a.tipo === t)) ?? null
}

export const placar = (ok: number | null, total: number | null) => (total ? `${ok ?? 0}/${total}` : null)
