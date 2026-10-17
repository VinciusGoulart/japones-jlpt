// Regra crítica (DESIGN §11): ele digita japonês com ibus-mozc, e o Enter que
// confirma a conversão do IME NUNCA pode enviar a resposta nem avançar.
//
// Três defesas, porque cada navegador erra de um jeito:
//  1. event.isComposing — o caminho normal (Chrome e Firefox);
//  2. keyCode 229 — o keydown "processado pelo IME" (Safari e alguns ibus mandam
//     o compositionend ANTES do keydown, com isComposing já falso);
//  3. uma janela curta depois do compositionend, pelo mesmo motivo do item 2.

let compondo = false
let fimDaComposicao = 0
const JANELA_MS = 80

export function instalarRastreioIme(): void {
  document.addEventListener('compositionstart', () => { compondo = true }, true)
  document.addEventListener('compositionend', () => {
    compondo = false
    fimDaComposicao = performance.now()
  }, true)
  // composição abandonada (troca de foco sem compositionend) não pode travar o Enter para sempre
  document.addEventListener('focusout', () => { compondo = false }, true)
}

type Tecla = Pick<KeyboardEvent, 'isComposing' | 'keyCode'>

export function emComposicao(e: Tecla): boolean {
  return e.isComposing || e.keyCode === 229 || compondo || performance.now() - fimDaComposicao < JANELA_MS
}

/** Enter de verdade: não é do IME, não é repetição, sem Shift/Alt. */
export function enterDeVerdade(e: KeyboardEvent): boolean {
  return e.key === 'Enter' && !e.repeat && !e.shiftKey && !e.altKey && !emComposicao(e)
}
