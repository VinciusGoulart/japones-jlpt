// Famílias de erro: os grupos do §4.2 do DESIGN juntados em 5 + "Outros".
//
// Por quê: o empilhado "por grupo" do contrato tem 15 grupos possíveis (e o
// texto é livre, então aparecem novos). Uma pilha com 15 cores é ilegível e
// nenhuma paleta separa tantas para daltônicos; a skill de dataviz manda parar
// em ~5 e dobrar o resto. A tabela de categorias, ao lado do gráfico, continua
// com a granularidade inteira, e a dica do gráfico abre cada família nos grupos.
//
// A cor segue a FAMÍLIA, nunca a posição no ranking: trocar o período não pode
// repintar "Partículas" de outra cor.
import { COR_OUTROS, SERIES } from '@/components/graficos/formato'

export type IdFamilia = 'particula' | 'formas' | 'escrita' | 'vocabulario' | 'gramatica' | 'outros'

export interface Familia {
  id: IdFamilia
  rotulo: string
  cor: string
  grupos: string[]
}

export const FAMILIAS: Familia[] = [
  { id: 'particula', rotulo: 'Partículas', cor: SERIES[0], grupos: ['particula'] },
  // conjugar verbo e ligar adjetivo são a mesma máquina de formas (05/10–16/10: て/た, 難しいで)
  { id: 'formas', rotulo: 'Formas e conjugação', cor: SERIES[1], grupos: ['forma-te', 'forma-ta', 'conjugacao', 'adjetivo'] },
  { id: 'escrita', rotulo: 'Kana e kanji', cor: SERIES[2], grupos: ['kana', 'katakana', 'leitura-kanji'] },
  { id: 'vocabulario', rotulo: 'Vocabulário e sentido', cor: SERIES[3], grupos: ['vocabulario', 'sentido'] },
  { id: 'gramatica', rotulo: 'Gramática e registro', cor: SERIES[4], grupos: ['gramatica', 'iru-aru', 'registro', 'ordem'] },
  { id: 'outros', rotulo: 'Outros', cor: COR_OUTROS, grupos: [] },
]

const POR_GRUPO = new Map(FAMILIAS.flatMap((f) => f.grupos.map((g) => [g, f] as const)))
const OUTROS = FAMILIAS[FAMILIAS.length - 1]

/** A família de um grupo; o que não está no §4.2 (inclusive 'outro') cai em Outros. */
export const familiaDe = (grupo: string): Familia => POR_GRUPO.get(grupo) ?? OUTROS

/** O grupo de uma categoria: o prefixo antes do ':' (a mesma regra do painel.py). */
export const grupoDe = (categoria: string) => categoria.split(':', 1)[0]
