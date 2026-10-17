import type { ReactNode } from 'react'
import { Anchor, Flag, Repeat } from 'lucide-react'
import { Vazio } from '@/components/Estados'
import { TextoMisto } from '@/components/Ja'
import { Secao } from '@/pages/hoje/Secao'
import type { StatusAnki } from '@/api/types'

/** "Japonês::Fase 0 - Kana::Hiragana" → "Hiragana": na lista, só o fim do caminho cabe. */
const ultimoNivel = (baralho: string) => baralho.split('::').pop() ?? baralho

function Lista({ itens, vazio }: { itens: { frente: string; baralho: string; n?: ReactNode }[]; vazio: string }) {
  if (itens.length === 0) return <Vazio>{vazio}</Vazio>
  return (
    <ul className="divide-y">
      {itens.map((x, i) => (
        <li key={`${x.frente}-${i}`} className="flex items-baseline gap-3 py-1.5 first:pt-0 last:pb-0">
          <span className="min-w-0 flex-1">
            <span className="text-base leading-snug">
              <TextoMisto texto={x.frente} classeJa="text-lg" />
            </span>
            <span className="block truncate text-xs text-muted-foreground" title={x.baralho}>
              {ultimoNivel(x.baralho)}
            </span>
          </span>
          {x.n !== undefined && <span className="shrink-0 text-sm font-medium tabular-nums">{x.n}</span>}
        </li>
      ))}
    </ul>
  )
}

export function Listas({ status }: { status: StatusAnki }) {
  return (
    <div className="grid items-start gap-6 md:grid-cols-3">
      <Secao titulo="Em loop" icone={<Repeat />} acao={<span className="text-xs text-muted-foreground">Again em 7 dias</span>}>
        <Lista
          itens={status.em_loop.map((x) => ({ frente: x.frente, baralho: x.baralho, n: `${x.again_7d}×` }))}
          vazio="Nenhum cartão apertado em Again repetidas vezes nos últimos 7 dias."
        />
      </Secao>
      <Secao titulo="Travam" icone={<Anchor />} acao={<span className="text-xs text-muted-foreground">lapsos</span>}>
        <Lista
          itens={status.travam.map((x) => ({ frente: x.frente, baralho: x.baralho, n: x.lapses }))}
          vazio="Nenhum cartão com lapsos repetidos (esqueceu depois de já ter aprendido)."
        />
      </Secao>
      <Secao titulo="Com bandeira" icone={<Flag />}>
        <Lista itens={status.bandeira} vazio="Nenhum cartão com bandeira." />
      </Secao>
    </div>
  )
}
