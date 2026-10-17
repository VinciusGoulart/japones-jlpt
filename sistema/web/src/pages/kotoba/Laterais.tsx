import { useState } from 'react'
import { BookOpen, History, Layers, ListPlus, Search, Star } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga, FonteFora, Vazio } from '@/components/Estados'
import { Ja, TextoMisto } from '@/components/Ja'
import { useKotobaHistorico, useKotobaListas } from '@/api/queries'
import { ehErro, type ConsultaKotoba } from '@/api/types'
import { dataCurta, ddmm, diaDeEstudoLocal, paraIso, relativo } from '@/lib/datas'
import { cn } from '@/lib/utils'
import { Secao } from '../hoje/Secao'
import { dividirRotulo } from './rotulos'

const DIAS = 30

export interface AcoesKotoba {
  /** busca de novo; `verbete` = o ent_seq que ele abriu (fica destacado nos resultados) */
  onBuscar: (termo: string, verbete?: number | null) => void
  onKanji: (k: string) => void
}

function Carregando({ linhas = 4 }: { linhas?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: linhas }, (_, i) => (
        <Skeleton key={i} className="h-7" />
      ))}
    </div>
  )
}

// ------------------------------------------------------------------ candidatas a cartão

export function Candidatas({ onBuscar }: Pick<AcoesKotoba, 'onBuscar'>) {
  const q = useKotobaHistorico(DIAS)
  return (
    <Secao titulo="Candidatas a cartão" icone={<ListPlus />}>
      <p className="mb-3 text-xs leading-relaxed text-muted-foreground">
        Palavras que você abriu e que não são campo de nenhuma nota do Anki. É uma pista, não certeza: o cartão pode estar noutra forma (
        <Ja>たべます</Ja> no lugar de <Ja>食べる</Ja>).
      </p>
      {q.isPending ? (
        <Carregando linhas={3} />
      ) : q.isError ? (
        <ErroCarga erro={q.error} tentar={() => q.refetch()} />
      ) : ehErro(q.data) ? (
        <FonteFora nome="Kotoba" erro={q.data.erro} />
      ) : q.data.sem_cartao.length === 0 ? (
        <Vazio>Nenhuma: tudo o que você abriu nos últimos {DIAS} dias já aparece no Anki.</Vazio>
      ) : (
        <ul className="-mx-1.5">
          {q.data.sem_cartao.map((c) => {
            const [, glosa] = dividirRotulo(c.rotulo)
            return (
              <li key={c.palavra}>
                <button
                  type="button"
                  onClick={() => onBuscar(c.palavra)}
                  className="flex w-full items-center gap-2 rounded-md px-1.5 py-1.5 text-left hover:bg-muted"
                >
                  <span className="min-w-0 flex-1 truncate">
                    <Ja className="text-base">{c.palavra}</Ja>
                    {c.leitura && c.leitura !== c.palavra && <Ja className="ml-1.5 text-xs text-muted-foreground">{c.leitura}</Ja>}
                    {glosa && <span className="ml-1.5 text-sm text-muted-foreground">{glosa}</span>}
                  </span>
                  <span className="shrink-0 text-xs text-muted-foreground tabular-nums" title={`aberta ${c.vezes} vez(es); a última em ${ddmm(c.ultima)}`}>
                    {c.vezes > 1 && <span className="mr-1.5 font-medium text-foreground">{c.vezes}×</span>}
                    {ddmm(c.ultima)}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </Secao>
  )
}

// ------------------------------------------------------------------ histórico

const TIPO = {
  query: { icone: Search, titulo: 'busca' },
  entry: { icone: BookOpen, titulo: 'abriu o verbete' },
  kanji: { icone: null, titulo: 'abriu a ficha do kanji' },
} as const

function LinhaConsulta({ c, onBuscar, onKanji }: { c: ConsultaKotoba } & AcoesKotoba) {
  const [texto, glosa] = dividirRotulo(c.rotulo)
  const t = TIPO[c.tipo] ?? TIPO.query
  const Icone = t.icone
  const abrir = () => {
    if (c.tipo === 'kanji' && c.kanji) onKanji(c.kanji)
    else if (c.tipo === 'entry' && c.palavra) onBuscar(c.palavra, c.ent_seq)
    else onBuscar(c.consulta ?? texto)
  }
  return (
    <li>
      <button type="button" onClick={abrir} className="flex w-full items-center gap-2 rounded-md px-1.5 py-1 text-left hover:bg-muted" title={t.titulo}>
        {/* a hora do relógio: a consulta das 02:18 de sábado aparece no dia de estudo de sexta */}
        <span className="w-9 shrink-0 text-xs text-muted-foreground tabular-nums">{c.quando.slice(11, 16)}</span>
        {Icone ? (
          <Icone className="size-3.5 shrink-0 text-muted-foreground" aria-label={t.titulo} />
        ) : (
          <Ja className="flex size-3.5 shrink-0 items-center justify-center rounded-[3px] border border-muted-foreground/60 text-[0.55rem] leading-none text-muted-foreground" aria-label={t.titulo}>
            字
          </Ja>
        )}
        <span className={cn('min-w-0 flex-1 truncate', c.tipo === 'query' && 'text-muted-foreground')}>
          <TextoMisto texto={texto} classeJa="text-base text-foreground" />
          {glosa && <span className="ml-1.5 text-sm text-muted-foreground">{glosa}</span>}
        </span>
        {c.tem_cartao === true && <Layers className="size-3.5 shrink-0 text-ok" aria-label="tem cartão" />}
        {c.tem_cartao === false && <span className="shrink-0 text-[0.7rem] text-aviso">sem cartão</span>}
      </button>
    </li>
  )
}

const POR_DIA = 8

function Dia({ data, consultas, hoje, ...acoes }: { data: string; consultas: ConsultaKotoba[]; hoje: string } & AcoesKotoba) {
  const [todas, setTodas] = useState(false)
  const visiveis = todas ? consultas : consultas.slice(0, POR_DIA)
  return (
    <section>
      <h3 className="mb-0.5 flex items-baseline justify-between gap-2 px-1.5 text-xs font-medium">
        <span className="first-letter:uppercase">{dataCurta(data)}</span>
        <span className="font-normal text-muted-foreground">
          {relativo(data, hoje)} · {consultas.length} consulta{consultas.length > 1 ? 's' : ''}
        </span>
      </h3>
      <ul>
        {visiveis.map((c, i) => (
          <LinhaConsulta key={`${c.quando}-${i}`} c={c} {...acoes} />
        ))}
      </ul>
      {consultas.length > POR_DIA && (
        <button type="button" onClick={() => setTodas((x) => !x)} className="px-1.5 pt-0.5 text-xs text-primary hover:underline">
          {todas ? 'menos' : `mais ${consultas.length - POR_DIA} deste dia`}
        </button>
      )}
    </section>
  )
}

export function Historico(acoes: AcoesKotoba) {
  const q = useKotobaHistorico(DIAS)
  const [dias, setDias] = useState(3)
  // o dia de estudo vira às 04:00, como o servidor agrupa (DESIGN §5)
  const hoje = paraIso(diaDeEstudoLocal())
  return (
    <Secao titulo="Histórico" icone={<History />} acao={<span className="text-xs text-muted-foreground">{DIAS} dias</span>}>
      {q.isPending ? (
        <Carregando />
      ) : q.isError ? (
        <ErroCarga erro={q.error} tentar={() => q.refetch()} />
      ) : ehErro(q.data) ? (
        <FonteFora nome="Kotoba" erro={q.data.erro} />
      ) : q.data.dias.length === 0 ? (
        <Vazio>Nenhuma consulta no Kotoba nos últimos {DIAS} dias.</Vazio>
      ) : (
        <div className="-mx-1.5 space-y-4">
          {q.data.aviso && <p className="px-1.5 text-xs text-aviso">{q.data.aviso}</p>}
          {q.data.dias.slice(0, dias).map((d) => (
            <Dia key={d.data} data={d.data} consultas={d.consultas} hoje={hoje} {...acoes} />
          ))}
          {q.data.dias.length > dias && (
            <button type="button" onClick={() => setDias((n) => n + 5)} className="px-1.5 text-sm text-primary hover:underline">
              mais {Math.min(5, q.data.dias.length - dias)} dias de estudo
            </button>
          )}
        </div>
      )}
    </Secao>
  )
}

// ------------------------------------------------------------------ listas

export function Listas({ onBuscar, onKanji }: AcoesKotoba) {
  const q = useKotobaListas()
  return (
    <Secao titulo="Listas" icone={<Star />}>
      {q.isPending ? (
        <Carregando linhas={1} />
      ) : q.isError ? (
        <ErroCarga erro={q.error} tentar={() => q.refetch()} />
      ) : ehErro(q.data) ? (
        <FonteFora nome="Kotoba" erro={q.data.erro} />
      ) : q.data.length === 0 ? (
        <Vazio>Nenhuma lista no Kotoba.</Vazio>
      ) : (
        <ul className="space-y-3">
          {q.data.map((l) => (
            <li key={l.id} className="space-y-1.5">
              <p className="flex items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-1.5 font-medium">
                  {l.favoritos && <Star className="size-3.5 fill-aviso text-aviso" />}
                  {l.nome}
                </span>
                <span className="text-xs text-muted-foreground tabular-nums">{l.total === 0 ? 'vazia' : `${l.total} ite${l.total > 1 ? 'ns' : 'm'}`}</span>
              </p>
              {l.itens.length > 0 && (
                <ul className="flex flex-wrap gap-1.5">
                  {l.itens.map((it, i) => {
                    const termo = it.palavra ?? String(it.ref)
                    return (
                      <li key={`${it.tipo}-${it.ref}-${i}`}>
                        <button
                          type="button"
                          onClick={() => (it.tipo === 'kanji' ? onKanji(termo) : onBuscar(termo))}
                          title={it.glosa_pt ?? undefined}
                          className="rounded-md border px-2 py-0.5 hover:bg-muted"
                        >
                          <Ja className="text-base">{termo}</Ja>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </Secao>
  )
}
