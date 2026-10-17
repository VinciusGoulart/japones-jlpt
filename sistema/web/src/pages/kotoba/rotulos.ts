// O Kotoba devolve a classe gramatical e as marcas de uso com os códigos do
// JMdict (v5t, vt, uk, hum…). Aqui eles viram português; código que não está
// na tabela aparece cru, para nunca esconder informação do dicionário.

const CLASSE: Record<string, string> = {
  n: 'substantivo',
  'n-adv': 'substantivo adverbial',
  'n-t': 'substantivo de tempo',
  'n-suf': 'substantivo sufixo',
  'n-pref': 'substantivo prefixo',
  'n-pr': 'nome próprio',
  pn: 'pronome',
  num: 'numeral',
  ctr: 'contador',
  pref: 'prefixo',
  suf: 'sufixo',
  prt: 'partícula',
  conj: 'conjunção',
  int: 'interjeição',
  exp: 'expressão',
  adv: 'advérbio',
  'adv-to': 'advérbio com と',
  'adj-i': 'adjetivo い',
  'adj-ix': 'adjetivo い (いい/よい)',
  'adj-na': 'adjetivo な',
  'adj-no': 'leva の',
  'adj-pn': 'pré-nominal',
  'adj-f': 'pré-nominal',
  'adj-t': 'adjetivo たる',
  aux: 'auxiliar',
  'aux-v': 'verbo auxiliar',
  'aux-adj': 'adjetivo auxiliar',
  cop: 'cópula',
  unc: 'sem classe',
  v1: 'verbo ichidan',
  'v1-s': 'verbo ichidan (especial)',
  v5aru: 'verbo godan (-aru)',
  v5b: 'verbo godan (ぶ)',
  v5g: 'verbo godan (ぐ)',
  v5k: 'verbo godan (く)',
  'v5k-s': 'verbo godan (行く)',
  v5m: 'verbo godan (む)',
  v5n: 'verbo godan (ぬ)',
  v5r: 'verbo godan (る)',
  'v5r-i': 'verbo godan (る, irregular)',
  v5s: 'verbo godan (す)',
  v5t: 'verbo godan (つ)',
  v5u: 'verbo godan (う)',
  'v5u-s': 'verbo godan (う, especial)',
  vk: 'verbo 来る',
  vs: 'vira verbo com する',
  'vs-i': 'verbo com する',
  'vs-s': 'verbo する (especial)',
  'vs-c': 'verbo す (arcaico)',
  vz: 'verbo -ずる',
  vt: 'transitivo',
  vi: 'intransitivo',
}

const MARCA: Record<string, string> = {
  uk: 'em geral em kana',
  hon: 'honorífico',
  hum: 'humilde',
  pol: 'polido',
  form: 'formal',
  col: 'coloquial',
  fam: 'familiar',
  male: 'fala masculina',
  fem: 'fala feminina',
  vulg: 'vulgar',
  sl: 'gíria',
  'net-sl': 'gíria da internet',
  joc: 'jocoso',
  derog: 'pejorativo',
  sens: 'sensível',
  arch: 'arcaico',
  obs: 'obsoleto',
  dated: 'antiquado',
  hist: 'histórico',
  rare: 'raro',
  abbr: 'abreviação',
  id: 'expressão idiomática',
  'on-mim': 'onomatopeia',
  proverb: 'provérbio',
  yoji: 'yojijukugo',
  poet: 'poético',
  euph: 'eufemismo',
  chn: 'fala infantil',
  child: 'fala infantil',
}

export function rotuloClasse(codigo: string): string {
  // v2*, v4* e companhia: as conjugações do japonês clássico, que não fazem diferença aqui
  return CLASSE[codigo] ?? (/^v[24]/.test(codigo) ? 'verbo arcaico' : codigo)
}

export function rotuloMarca(codigo: string): string {
  return MARCA[codigo] ?? codigo
}

/** "verbo godan (つ) · transitivo" */
export function classesEmTexto(codigos: string[]): string {
  return [...new Set(codigos.map(rotuloClasse))].join(' · ')
}

/** Ano escolar do KANJIDIC: 1–6 = primário japonês; 8 = o resto dos jōyō; 9–10 = jinmeiyō (kanji de nomes). */
export function rotuloSerie(serie: number): string {
  if (serie >= 1 && serie <= 6) return `${serie}º ano`
  if (serie === 8) return 'secundário'
  if (serie === 9 || serie === 10) return 'jinmeiyō (nomes)'
  return `série ${serie}`
}

/** "持つ · segurar (na mão)" → ["持つ", "segurar (na mão)"] */
export function dividirRotulo(rotulo: string): [string, string | null] {
  const i = rotulo.indexOf(' · ')
  return i === -1 ? [rotulo, null] : [rotulo.slice(0, i), rotulo.slice(i + 3)]
}

const KANJI = /[㐀-䶿一-鿿豈-﫿]/

export function ehKanji(c: string): boolean {
  return KANJI.test(c)
}
