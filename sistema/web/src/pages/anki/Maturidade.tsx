import { MousePointerClick, Sprout } from 'lucide-react'
import { Secao } from '@/pages/hoje/Secao'
import { BarraEmpilhada } from '@/components/graficos/BarraEmpilhada'
import { Amostra } from '@/components/graficos/Legenda'
import { COR_OUTROS, inteiro, pctDeFracao } from '@/components/graficos/formato'
import type { GraficosAnki, StatusAnki } from '@/api/types'

// Ordinal: a ordem da vida de um cartão. Um tom só, do claro (novo) ao escuro
// (maduro), para a ordem estar na própria cor; suspenso fica cinza, fora da escada.
const ESTAGIOS = [
  { chave: 'novos', rotulo: 'Novos', nota: 'nunca vistos', cor: 'var(--viz-ord-1)' },
  { chave: 'aprendendo', rotulo: 'Aprendendo', nota: 'nos primeiros passos', cor: 'var(--viz-ord-2)' },
  { chave: 'jovens', rotulo: 'Jovens', nota: 'intervalo < 21 dias', cor: 'var(--viz-ord-3)' },
  { chave: 'maduros', rotulo: 'Maduros', nota: 'intervalo ≥ 21 dias', cor: 'var(--viz-ord-4)' },
  { chave: 'suspensos', rotulo: 'Suspensos', nota: 'suspensos ou enterrados', cor: COR_OUTROS },
] as const

export function Maturidade({ maturidade }: { maturidade: GraficosAnki['maturidade'] }) {
  const total = ESTAGIOS.reduce((s, e) => s + maturidade[e.chave], 0)
  return (
    <Secao titulo="Maturidade da coleção" icone={<Sprout />} acao={<span className="text-xs text-muted-foreground">{inteiro(total)} cartões</span>}>
      <div className="space-y-4">
        <BarraEmpilhada
          rotulo="Cartões por estágio"
          altura={18}
          partes={ESTAGIOS.map((e) => ({
            chave: e.chave,
            rotulo: e.rotulo,
            valor: maturidade[e.chave],
            cor: e.cor,
            dica: `${e.rotulo}: ${inteiro(maturidade[e.chave])} (${total ? pctDeFracao(maturidade[e.chave] / total) : '0%'})`,
          }))}
        />
        <ul className="divide-y text-sm">
          {ESTAGIOS.map((e) => (
            <li key={e.chave} className="flex items-center gap-2 py-1.5">
              <Amostra cor={e.cor} />
              <span>{e.rotulo}</span>
              <span className="text-xs text-muted-foreground">{e.nota}</span>
              <span className="ml-auto font-medium tabular-nums">{inteiro(maturidade[e.chave])}</span>
              <span className="w-10 text-right text-xs text-muted-foreground tabular-nums">{total ? pctDeFracao(maturidade[e.chave] / total) : '—'}</span>
            </li>
          ))}
        </ul>
      </div>
    </Secao>
  )
}

const BOTOES = [
  { chave: 'again', rotulo: 'Again', nota: 'esqueci' },
  { chave: 'hard', rotulo: 'Hard', nota: 'lembrei com esforço' },
  { chave: 'good', rotulo: 'Good', nota: 'lembrei' },
  { chave: 'easy', rotulo: 'Easy', nota: 'fácil demais' },
] as const

/**
 * Os botões apertados nos últimos 30 dias. Barras de uma cor só: são quatro
 * categorias de um mesmo dado, e o rótulo (não a cor) diz qual é a de erro.
 */
export function Botoes({ botoes }: { botoes: StatusAnki['botoes_30d_pct'] }) {
  const maior = Math.max(1, ...BOTOES.map((b) => botoes[b.chave]))
  return (
    <Secao titulo="Botões em 30 dias" icone={<MousePointerClick />}>
      <ul className="space-y-2.5">
        {BOTOES.map((b) => (
          <li key={b.chave} className="grid grid-cols-[7.5rem_1fr_2.5rem] items-center gap-3 text-sm">
            <span className="leading-tight">
              <span className="font-medium">{b.rotulo}</span>
              <span className="block text-xs text-muted-foreground">{b.nota}</span>
            </span>
            <span className="h-3 overflow-hidden rounded-r-[4px]">
              <span className="block h-full rounded-r-[4px]" style={{ width: `${(botoes[b.chave] / maior) * 100}%`, background: 'var(--viz-s1)' }} />
            </span>
            <span className="text-right font-medium tabular-nums">{botoes[b.chave]}%</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-muted-foreground">Porcentagem das respostas; o arredondamento pode somar 99% ou 101%.</p>
    </Secao>
  )
}
