import { useState, type ReactNode } from 'react'
import { Lightbulb } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga, Vazio } from '@/components/Estados'
import { Ja } from '@/components/Ja'
import { Markdown } from '@/components/Markdown'
import { useKotobaKanji } from '@/api/queries'
import type { KanjiKotoba } from '@/api/types'
import { rotuloSerie } from './rotulos'

/** A ficha de um kanji, num painel lateral: abre por cima do verbete sem perder a busca. */
export function FichaKanji({ literal, onFechar }: { literal: string | null; onFechar: () => void }) {
  // o último kanji continua desenhado enquanto o painel faz a animação de fechar
  const [mostrado, setMostrado] = useState(literal)
  if (literal && literal !== mostrado) setMostrado(literal)

  return (
    <Sheet open={!!literal} onOpenChange={(aberto) => !aberto && onFechar()}>
      <SheetContent className="gap-0 overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-md">
        {mostrado && <Conteudo literal={mostrado} />}
      </SheetContent>
    </Sheet>
  )
}

function Conteudo({ literal }: { literal: string }) {
  const q = useKotobaKanji(literal)
  const k = q.data

  return (
    <>
      <SheetHeader className="flex-row items-center gap-4 border-b p-5 pr-12">
        <SheetTitle>
          <Ja className="text-7xl leading-none font-normal">{literal}</Ja>
        </SheetTitle>
        <div className="min-w-0 space-y-1">
          {q.isPending ? (
            <Skeleton className="h-5 w-40" />
          ) : k ? (
            <>
              <SheetDescription className="text-base font-medium text-foreground">
                {k.significados_pt.join(', ') || k.significados_en.join(', ')}
                {k.significados_pt_auto && (
                  <Badge variant="outline" className="ml-2 h-4 border-aviso/40 px-1.5 align-[0.1em] text-[0.7rem] font-normal text-aviso">
                    tradução automática
                  </Badge>
                )}
              </SheetDescription>
              {k.significados_pt.length > 0 && k.significados_en.length > 0 && (
                <p lang="en" className="text-sm text-muted-foreground">
                  {k.significados_en.join(', ')}
                </p>
              )}
            </>
          ) : (
            <SheetDescription>Ficha do kanji</SheetDescription>
          )}
        </div>
      </SheetHeader>

      <div className="space-y-6 p-5">
        {q.isPending ? (
          <div className="space-y-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-24" />
            <Skeleton className="h-32" />
          </div>
        ) : q.isError ? (
          <ErroCarga erro={q.error} tentar={() => q.refetch()} />
        ) : !k ? (
          <Vazio>
            O kanji <Ja className="text-base">{literal}</Ja> não está no dicionário do Kotoba.
          </Vazio>
        ) : (
          <Ficha k={k} />
        )}
      </div>
    </>
  )
}

function Bloco({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{titulo}</h3>
      {children}
    </section>
  )
}

/** も.つ → も + つ apagado: o ponto do KANJIDIC separa o radical do okurigana. */
function Kun({ kun }: { kun: string }) {
  const [raiz, okuri] = kun.split('.')
  return (
    <Ja className="rounded-md bg-muted px-2 py-0.5 text-lg">
      {raiz}
      {okuri && <span className="text-muted-foreground">{okuri}</span>}
    </Ja>
  )
}

function Ficha({ k }: { k: KanjiKotoba }) {
  const numeros = [
    k.tracos !== null && { rotulo: 'traços', valor: String(k.tracos) },
    k.jlpt !== null && { rotulo: 'JLPT', valor: `N${k.jlpt}` },
    k.serie !== null && { rotulo: 'escola japonesa', valor: rotuloSerie(k.serie) },
    k.frequencia !== null && { rotulo: 'frequência', valor: `nº ${k.frequencia}` },
  ].filter((x): x is { rotulo: string; valor: string } => !!x)

  const v = k.radical?.variante ?? null

  return (
    <>
      {numeros.length > 0 && (
        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {numeros.map((n) => (
            <div key={n.rotulo} className="rounded-lg bg-muted/60 px-3 py-2">
              <dt className="text-xs text-muted-foreground">{n.rotulo}</dt>
              <dd className="font-medium tabular-nums">{n.valor}</dd>
            </div>
          ))}
        </dl>
      )}

      {(k.on.length > 0 || k.kun.length > 0) && (
        <Bloco titulo="Leituras">
          <div className="space-y-2">
            {k.on.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="w-9 text-xs text-muted-foreground" title="on'yomi: a leitura que veio do chinês">on</span>
                {k.on.map((o) => (
                  <Ja key={o} className="rounded-md bg-muted px-2 py-0.5 text-lg">
                    {o}
                  </Ja>
                ))}
              </div>
            )}
            {k.kun.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="w-9 text-xs text-muted-foreground" title="kun'yomi: a leitura japonesa; em cinza, o okurigana">
                  kun
                </span>
                {k.kun.map((x) => (
                  <Kun key={x} kun={x} />
                ))}
              </div>
            )}
          </div>
        </Bloco>
      )}

      {k.mnemonico && (
        <Bloco titulo="Para lembrar">
          <div className="space-y-3 rounded-xl border border-aviso/30 bg-aviso-bg/60 p-4">
            <div className="flex gap-2.5">
              <Lightbulb className="mt-1 size-4 shrink-0 text-aviso" />
              <Markdown texto={k.mnemonico.significado} className="text-base" />
            </div>
            {k.mnemonico.leitura_frase && (
              <p className="flex items-baseline gap-2.5 border-t border-aviso/20 pt-3">
                {k.mnemonico.leitura_kana && <Ja className="shrink-0 text-xl font-medium">{k.mnemonico.leitura_kana}</Ja>}
                <span className="leading-relaxed">{k.mnemonico.leitura_frase}</span>
              </p>
            )}
          </div>
        </Bloco>
      )}

      {k.radical && (
        <Bloco titulo="Radical">
          <div className="flex items-start gap-3">
            <Ja className="text-4xl leading-none">{k.radical.glifo}</Ja>
            <div className="min-w-0 text-sm leading-relaxed">
              <p>
                <span className="font-medium">{k.radical.significado_pt}</span>
                <span className="text-muted-foreground">
                  {' · '}
                  <Ja className="text-base text-foreground">{k.radical.nome}</Ja> · nº {k.radical.numero}
                </span>
              </p>
              {v?.glifo && (
                <p className="text-muted-foreground">
                  aqui como <Ja className="text-lg text-foreground">{v.glifo}</Ja>
                  {v.nome && (
                    <>
                      {' '}
                      <Ja className="text-base text-foreground">{v.nome}</Ja>
                    </>
                  )}
                  {v.significado_pt && <> · {v.significado_pt}</>}
                </p>
              )}
            </div>
          </div>
        </Bloco>
      )}

      {k.componentes.length > 0 && (
        <Bloco titulo="Componentes">
          <ul className="flex flex-wrap gap-2">
            {k.componentes.map((c) => (
              <li key={c.glifo} className="flex items-center gap-2 rounded-lg border px-2.5 py-1.5">
                <Ja className="text-2xl leading-none">{c.glifo}</Ja>
                <span className="text-sm">{c.nome_pt}</span>
              </li>
            ))}
          </ul>
        </Bloco>
      )}
    </>
  )
}
