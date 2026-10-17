import { useState } from 'react'
import { History, Loader2, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga, Vazio } from '@/components/Estados'
import { TextoMisto } from '@/components/Ja'
import { Secao } from '@/pages/hoje/Secao'
import { useRegistro } from '@/api/queries'
import type { RegistroAntigo as Anotacao } from '@/api/types'
import { dataTabela } from '@/lib/datas'
import { useAtrasado } from '@/lib/useAtrasado'
import { cn } from '@/lib/utils'

/** o api.registro pede 20; se vierem 20, há (talvez) mais */
const LIMITE = 20
/** termos que existem no registro (conferido em 17/10): servem de porta de entrada */
const SUGESTOES = ['に', 'を', 'katakana', 'dakuten', 'adjetivo', 'vogal longa']

const escapar = (t: string) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** Marca o termo buscado (sem diferenciar maiúscula, como o LIKE do SQLite) sem perder o lang="ja". */
function Realce({ texto, termo }: { texto: string; termo: string }) {
  const partes = texto.split(new RegExp(`(${escapar(termo)})`, 'i'))
  return (
    <>
      {partes.map((p, i) =>
        i % 2 === 1 ? (
          <mark key={i} className="rounded-sm bg-aviso-bg px-0.5 text-foreground ring-1 ring-aviso/40">
            <TextoMisto texto={p} />
          </mark>
        ) : (
          <TextoMisto key={i} texto={p} />
        ),
      )}
    </>
  )
}

/** Antes e depois do primeiro acerto, no resumo de uma anotação longa. */
const ANTES = 140
const DEPOIS = 240

/**
 * O trecho em volta do primeiro acerto. As anotações de um dia chegam a 2.000
 * caracteres: cortar no começo escondia justamente a palavra buscada, e ele não
 * via por que a anotação tinha aparecido.
 */
function janela(texto: string, termo: string): string {
  const i = texto.search(new RegExp(escapar(termo), 'i'))
  if (i < 0) return texto.slice(0, ANTES + DEPOIS) + ' …'
  const ini = Math.max(0, i - ANTES)
  const fim = Math.min(texto.length, i + termo.length + DEPOIS)
  // recomeça numa palavra inteira, não no meio dela
  const comeco = ini > 0 ? texto.indexOf(' ', ini) + 1 || ini : 0
  return `${comeco > 0 ? '… ' : ''}${texto.slice(comeco, fim)}${fim < texto.length ? ' …' : ''}`
}

function ItemRegistro({ a, termo }: { a: Anotacao; termo: string }) {
  const [aberto, setAberto] = useState(false)
  const longo = a.texto.length > ANTES + DEPOIS + 80
  // o log herdado separa os trechos de um dia com " | ": inteiro, cada um vira um parágrafo
  const trechos = longo && !aberto ? [janela(a.texto, termo).replace(/\s+\|\s+/g, ' · ')] : a.texto.split(/\s+\|\s+/)
  return (
    <li className="space-y-1.5 py-3 first:pt-0 last:pb-0">
      <p className="text-xs font-medium text-muted-foreground tabular-nums">{a.data ? dataTabela(a.data) : 'sem data'}</p>
      <div className="space-y-1.5 text-sm leading-relaxed">
        {trechos.map((t, i) => (
          <p key={i}>
            <Realce texto={t} termo={termo} />
          </p>
        ))}
      </div>
      {longo && (
        <Button variant="link" size="xs" className="h-auto px-0" onClick={() => setAberto((v) => !v)}>
          {aberto ? 'recolher' : 'ler tudo'}
        </Button>
      )}
    </li>
  )
}

/** Busca no log livre de antes do sistema (pontos_fracos): "isso já aconteceu antes?" */
export function RegistroAntigo() {
  const [busca, setBusca] = useState('')
  const termo = useAtrasado(busca.trim(), 300)
  const q = useRegistro(termo)

  return (
    <Secao titulo="Registro antigo" icone={<History />}>
      <div className="space-y-3">
        <p className="text-xs leading-relaxed text-muted-foreground">
          As anotações de pontos fracos de antes do sistema, em texto livre. Não têm categoria: a busca é por texto, e o mais novo vem
          primeiro.
        </p>
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="buscar (ex.: に, katakana, forma て)"
            className="h-9 pl-9"
            aria-label="Buscar no registro antigo"
          />
          {q.isFetching && <Loader2 className="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />}
        </div>

        {!termo ? (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Experimente:</span>
            {SUGESTOES.map((s) => (
              <Button key={s} variant="outline" size="xs" onClick={() => setBusca(s)}>
                <TextoMisto texto={s} />
              </Button>
            ))}
          </div>
        ) : q.isError ? (
          <ErroCarga erro={q.error} tentar={() => q.refetch()} />
        ) : q.isPending ? (
          <div className="space-y-2">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        ) : q.data.length === 0 ? (
          <Vazio>Nada com “{termo}” no registro antigo.</Vazio>
        ) : (
          <>
            <p className="text-xs text-muted-foreground">
              {q.data.length === LIMITE ? `As ${LIMITE} anotações mais novas com “${termo}” (pode haver mais).` : `${q.data.length} ${q.data.length === 1 ? 'anotação' : 'anotações'} com “${termo}”.`}
            </p>
            <ul className={cn('divide-y transition-opacity', q.isPlaceholderData && 'opacity-60')}>
              {q.data.map((a, i) => (
                <ItemRegistro key={`${a.data}-${i}-${a.texto.slice(0, 24)}`} a={a} termo={termo} />
              ))}
            </ul>
          </>
        )}
      </div>
    </Secao>
  )
}
