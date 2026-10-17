/** Mesmos critérios do normalizar() do servidor: NFKC, sem espaço nem pontuação. */
export function normalizar(t: string): string {
  return t.normalize('NFKC').replace(/[\s。、.,!?！？・「」]/g, '')
}

/** Tira a marcação de markdown para textos de uma linha só (eventos do calendário). */
export function semMarkdown(t: string): string {
  return t.replace(/\*\*|__|\*|_|`/g, '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').trim()
}

// kana, kanji, pontuação e formas de largura cheia
const JAPONES = /([　-〿぀-ヿㇰ-ㇿ㐀-䶿一-鿿豈-﫿＀-￯〜～]+)/

/** Divide um texto misto em trechos, marcando os japoneses (para lang="ja" e tamanho maior). */
export function trechos(t: string): { texto: string; ja: boolean }[] {
  return t
    .split(JAPONES)
    .filter(Boolean)
    .map((texto) => ({ texto, ja: JAPONES.test(texto) }))
}
