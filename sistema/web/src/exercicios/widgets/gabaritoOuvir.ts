// O gabarito do ouvir vem pronto para mostrar (DESIGN §10), mas em dois formatos:
// ditado → "o que foi dito"; compreensão → "o que foi dito → a opção certa".
// O widget, o Feedback e o Resumo precisam das duas metades separadas: a opção
// certa é marcada na lista, e o texto falado é a transcrição que ele lê depois.

export interface GabaritoOuvir {
  /** o texto que a voz leu */
  dito: string
  /** só na compreensão: a opção certa */
  certa: string | null
}

const SETA = ' → '

export function separarGabaritoOuvir(gabarito: string, opcoes?: string[]): GabaritoOuvir {
  if (!opcoes?.length) return { dito: gabarito, certa: null }
  // pelo FIM do gabarito, e não cortando na seta: uma opção em português pode ter "→" no meio
  const certa = opcoes.find((o) => gabarito.endsWith(SETA + o))
  if (certa) return { dito: gabarito.slice(0, -(SETA.length + certa.length)), certa }
  const i = gabarito.indexOf(SETA)
  return i === -1 ? { dito: gabarito, certa: null } : { dito: gabarito.slice(0, i), certa: gabarito.slice(i + SETA.length) }
}
