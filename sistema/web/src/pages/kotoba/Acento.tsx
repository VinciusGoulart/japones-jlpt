import type { Acento as AcentoKotoba } from '@/api/types'
import { cn } from '@/lib/utils'

// Kana pequeno não é mora sozinho: きょ é uma mora só. っ, ん e ー são moras inteiras.
const PEQUENOS = new Set([...'ゃゅょぁぃぅぇぉゎャュョァィゥェォヮ'])

function moras(kana: string): string[] {
  const r: string[] = []
  for (const c of kana) {
    if (PEQUENOS.has(c) && r.length) r[r.length - 1] += c
    else r.push(c)
  }
  return r
}

/**
 * Alto (true) ou baixo de cada mora, mais a partícula que viria depois (o último item).
 * Regra do japonês de Tóquio, que é a do NHK e a do Kotoba: a 1ª e a 2ª mora nunca têm
 * a mesma altura; `queda` = a mora depois da qual o tom cai (0 = não cai, heiban).
 * É a partícula que separa heiban (ela fica alta) de odaka (ela cai): por isso ela aparece.
 */
function alturas(n: number, queda: number): boolean[] {
  return Array.from({ length: n + 1 }, (_, i) => {
    const pos = i + 1
    if (queda === 1) return pos === 1
    if (queda === 0) return pos > 1
    return pos > 1 && pos <= queda
  })
}

function descrever(queda: number, n: number): string {
  if (queda === 0) return 'sem queda: sobe depois da 1ª mora e a partícula fica alta'
  if (queda === 1) return 'alto só na 1ª mora, depois cai'
  if (queda >= n) return 'cai depois da última mora: a partícula fica baixa'
  return `cai depois da ${queda}ª mora`
}

/** O contorno desenhado sobre o kana: linha em cima = alto, embaixo = baixo, traço vertical = muda. */
function Contorno({ ms, queda }: { ms: string[]; queda: number }) {
  const alto = alturas(ms.length, queda)
  return (
    <span lang="ja" aria-hidden className="inline-flex items-stretch font-ja text-xl leading-none">
      {[...ms, null].map((m, i) => (
        <span
          key={i}
          className={cn(
            'border-primary px-[0.12em] py-[0.3em]',
            alto[i] ? 'border-t-2' : 'border-b-2',
            i > 0 && alto[i - 1] !== alto[i] && 'border-l-2',
            // a partícula: só o traço, tracejado, para não parecer parte da palavra
            m === null && 'w-[0.9em] border-dashed opacity-60',
          )}
        >
          {m}
        </span>
      ))}
    </span>
  )
}

export function Acento({ acento }: { acento: AcentoKotoba }) {
  const ms = moras(acento.leitura)
  if (!ms.length || !acento.quedas.length) return null
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
      {acento.quedas.map((q, i) => (
        <div key={q} className="flex items-center gap-3" title="Linha em cima = tom alto; embaixo = baixo; o tracejado é a partícula que vem depois (が, は…)">
          <Contorno ms={ms} queda={q} />
          <p className="text-sm leading-snug">
            <span className="sr-only">Acento: </span>
            {descrever(q, ms.length)}
            {acento.padroes[i] && <span className="ml-1.5 text-muted-foreground">({acento.padroes[i]})</span>}
          </p>
        </div>
      ))}
    </div>
  )
}
