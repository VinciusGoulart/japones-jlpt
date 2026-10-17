import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Languages, Layers } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Ja } from '@/components/Ja'
import type { SentidoKotoba, VerbeteKotoba } from '@/api/types'
import { cn } from '@/lib/utils'
import { Acento } from './Acento'
import { classesEmTexto, ehKanji, rotuloMarca } from './rotulos'

/** A palavra com cada kanji clicável (abre a ficha); o kana fica como texto. */
export function Palavra({ texto, onKanji, className }: { texto: string; onKanji: (k: string) => void; className?: string }) {
  return (
    <Ja className={cn('font-medium', className)}>
      {[...texto].map((c, i) =>
        ehKanji(c) ? (
          <button
            key={i}
            type="button"
            onClick={() => onKanji(c)}
            title={`Ficha do kanji ${c}`}
            className="rounded-md underline decoration-primary/35 decoration-dotted decoration-2 underline-offset-[0.2em] outline-none hover:bg-accent hover:decoration-primary focus-visible:ring-2 focus-visible:ring-ring"
          >
            {c}
          </button>
        ) : (
          <span key={i}>{c}</span>
        ),
      )}
    </Ja>
  )
}

const mesmaClasse = (a: string[], b: string[]) => a.length === b.length && a.every((x, i) => x === b[i])

export function Verbete({
  v,
  principal,
  destaque,
  onKanji,
}: {
  v: VerbeteKotoba
  /** o primeiro resultado: mostra mais sentidos abertos */
  principal: boolean
  /** veio de um clique no histórico (?v=): é este o verbete que ele abriu */
  destaque: boolean
  onKanji: (k: string) => void
}) {
  const [ingles, setIngles] = useState(false)
  const [todos, setTodos] = useState(false)
  const ref = useRef<HTMLElement>(null)

  useEffect(() => {
    if (destaque) ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [destaque])

  // um verbete sem sentidos detalhados ainda tem as glosas soltas
  const sentidos: SentidoKotoba[] = v.sentidos.length
    ? v.sentidos
    : [{ classe: v.classe, misc: [], pt: v.glosas_pt, pt_auto: v.glosas_pt_auto.length > 0, en: v.glosas_en }]
  // 取る tem 18 sentidos: os primeiros bastam, e o que casou com a busca nunca fica escondido
  const limite = Math.max(principal ? 6 : 3, (v.sentido_casado ?? -1) + 1)
  const visiveis = todos ? sentidos : sentidos.slice(0, limite)
  const escondidos = sentidos.length - visiveis.length
  const temIngles = sentidos.some((s) => s.en.length > 0 && s.pt.length > 0)
  // usual_em_kana: a palavra vem em kana e o kanji fica como grafia alternativa
  const outraGrafia = v.grafia_kanji && v.grafia_kanji !== v.palavra ? v.grafia_kanji : null

  return (
    <article
      ref={ref}
      className={cn('space-y-4 rounded-xl border bg-card p-4 sm:p-5', destaque && 'ring-2 ring-primary/50')}
      aria-label={`${v.palavra} (${v.leitura})`}
    >
      <header className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          {/* a leitura vai inteira em cima, não como furigana: ruby espalharia もつ sobre o つ do okurigana */}
          {v.leitura !== v.palavra && <Ja className="block text-base text-muted-foreground sm:text-lg">{v.leitura}</Ja>}
          <Palavra texto={v.palavra} onKanji={onKanji} className={cn('leading-tight', principal ? 'text-5xl' : 'text-4xl')} />
          {outraGrafia && (
            <p className="mt-1 text-sm text-muted-foreground">
              em kanji <Palavra texto={outraGrafia} onKanji={onKanji} className="text-lg text-foreground" />
              {v.usual_em_kana && ' · em geral escrita em kana'}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {v.jlpt !== null && <Badge title={`Lista do JLPT N${v.jlpt}`}>N{v.jlpt}</Badge>}
          {v.comum && <Badge variant="secondary">comum</Badge>}
          {/* null = o Anki não abriu: sem a pista, melhor não dizer nada */}
          {v.tem_cartao === true && (
            <Badge className="bg-ok-bg text-ok" title="A palavra ou a leitura é um campo de alguma nota do Anki">
              <Layers /> tem cartão
            </Badge>
          )}
          {v.tem_cartao === false && (
            <Badge variant="outline" className="text-muted-foreground" title="Nenhuma nota do Anki tem esta palavra como campo inteiro (pode estar noutra forma)">
              sem cartão
            </Badge>
          )}
        </div>
      </header>

      {(v.classe.length > 0 || v.acento) && (
        <div className="space-y-2.5">
          {v.classe.length > 0 && <p className="text-sm text-muted-foreground">{classesEmTexto(v.classe)}</p>}
          {v.acento && <Acento acento={v.acento} />}
        </div>
      )}

      <ol className="space-y-1.5">
        {visiveis.map((s, i) => {
          const classePropria = i > 0 && !mesmaClasse(s.classe, sentidos[i - 1].classe) && s.classe.length > 0
          const soIngles = s.pt.length === 0
          // "em geral em kana" já está no cabeçalho quando a palavra vem em kana
          const marcas = v.usual_em_kana ? s.misc.filter((m) => m !== 'uk') : s.misc
          return (
            <li
              key={i}
              className={cn('flex gap-2.5 rounded-lg px-2 py-1', i === v.sentido_casado && 'bg-accent/70')}
              title={i === v.sentido_casado ? 'O sentido que casou com a busca' : undefined}
            >
              <span className="w-5 shrink-0 pt-0.5 text-right text-sm text-muted-foreground tabular-nums">{i + 1}.</span>
              <div className="min-w-0 space-y-0.5">
                {(classePropria || marcas.length > 0) && (
                  <p className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
                    {classePropria && <span>{classesEmTexto(s.classe)}</span>}
                    {marcas.map((m) => (
                      <Badge key={m} variant="outline" className="h-4 px-1.5 text-[0.7rem] font-normal text-muted-foreground">
                        {rotuloMarca(m)}
                      </Badge>
                    ))}
                  </p>
                )}
                <p className="leading-relaxed">
                  {soIngles ? (
                    <span lang="en" className="text-muted-foreground">
                      <span className="italic">só em inglês:</span> {s.en.join('; ')}
                    </span>
                  ) : (
                    s.pt.join('; ')
                  )}
                  {s.pt_auto && !soIngles && (
                    <Badge
                      variant="outline"
                      className="ml-2 h-4 border-aviso/40 px-1.5 align-[0.1em] text-[0.7rem] font-normal text-aviso"
                      title="Traduzida do inglês por máquina: confira no inglês se a nuance importar"
                    >
                      tradução automática
                    </Badge>
                  )}
                </p>
                {ingles && !soIngles && s.en.length > 0 && (
                  <p lang="en" className="text-sm text-muted-foreground">
                    {s.en.join('; ')}
                  </p>
                )}
              </div>
            </li>
          )
        })}
      </ol>

      {(escondidos > 0 || todos || temIngles) && (
        <footer className="flex flex-wrap gap-x-4 gap-y-1 border-t pt-3 text-sm">
          {(escondidos > 0 || todos) && sentidos.length > limite && (
            <button type="button" onClick={() => setTodos((t) => !t)} className="inline-flex items-center gap-1 text-primary hover:underline">
              <ChevronDown className={cn('size-4 transition-transform', todos && 'rotate-180')} />
              {todos ? 'menos sentidos' : `mais ${escondidos} sentido${escondidos > 1 ? 's' : ''}`}
            </button>
          )}
          {temIngles && (
            <button
              type="button"
              onClick={() => setIngles((x) => !x)}
              aria-pressed={ingles}
              className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
            >
              <Languages className="size-4" />
              {ingles ? 'esconder o inglês' : 'ver em inglês'}
            </button>
          )}
        </footer>
      )}
    </article>
  )
}
