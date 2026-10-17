import { useCallback, useEffect, useEffectEvent, useRef, useState } from 'react'
import { useSearchParams } from 'react-router'
import { Loader2, Search, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga, FonteFora, Vazio } from '@/components/Estados'
import { TextoMisto } from '@/components/Ja'
import { useKotobaBusca } from '@/api/queries'
import { ehErro } from '@/api/types'
import { emComposicao, enterDeVerdade } from '@/lib/ime'
import { useAtrasado } from '@/lib/useAtrasado'
import { cn } from '@/lib/utils'
import { FichaKanji } from './kotoba/FichaKanji'
import { Candidatas, Historico, Listas } from './kotoba/Laterais'
import { Verbete } from './kotoba/Verbete'

// O painel só LÊ o Kotoba (DESIGN §12.4). Sem link kotoba://: no Linux o atalho do
// app não registra o esquema e o link não abriria nada; o verbete vem inteiro aqui.

export function PaginaKotoba() {
  const [params, setParams] = useSearchParams()
  // a busca mora na URL (?q=): voltar do navegador ou de outra tela traz a mesma busca
  const q = (params.get('q') ?? '').trim()
  const verbete = Number(params.get('v')) || null
  const [kanji, setKanji] = useState<string | null>(null)
  const busca = useKotobaBusca(q)

  const irPara = useCallback(
    (termo: string, { verbete, substituir = false }: { verbete?: number | null; substituir?: boolean } = {}) => {
      setParams(
        (atual) => {
          const p = new URLSearchParams(atual)
          if (termo) p.set('q', termo)
          else p.delete('q')
          if (verbete) p.set('v', String(verbete))
          else p.delete('v')
          return p
        },
        { replace: substituir },
      )
    },
    [setParams],
  )

  // clique no histórico, nas candidatas ou nas listas: entra no histórico do navegador (dá para voltar)
  const buscarDeNovo = useCallback(
    (termo: string, ent?: number | null) => {
      irPara(termo, { verbete: ent })
      // no celular o histórico fica embaixo dos resultados
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [irPara],
  )

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Kotoba</h1>
        <p className="text-sm text-muted-foreground">o seu dicionário · o painel só lê</p>
      </header>

      <CampoBusca
        q={q}
        buscando={busca.isFetching}
        // digitando: troca a entrada da URL (sem encher o histórico do navegador letra a letra); Enter: entrada nova
        onBuscar={(termo, confirmado) => irPara(termo, { substituir: !confirmado })}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="min-w-0 space-y-3 lg:col-span-2" aria-label="Resultados">
          {!q ? (
            <Inicio onBuscar={buscarDeNovo} />
          ) : busca.isPending ? (
            <div className="space-y-3">
              <Skeleton className="h-56 rounded-xl" />
              <Skeleton className="h-40 rounded-xl" />
            </div>
          ) : busca.isError ? (
            <ErroCarga erro={busca.error} tentar={() => busca.refetch()} />
          ) : ehErro(busca.data) ? (
            <FonteFora nome="Kotoba" erro={busca.data.erro} />
          ) : busca.data.resultados.length === 0 ? (
            <Vazio>
              Nada para “<span className="font-ja">{q}</span>” no Kotoba.
            </Vazio>
          ) : (
            <div className={cn('space-y-3 transition-opacity', busca.isPlaceholderData && 'opacity-60')}>
              <p className="text-xs text-muted-foreground">
                {busca.data.resultados.length} resultado{busca.data.resultados.length > 1 ? 's' : ''}
                {busca.data.resultados.length >= 20 && ' (os 20 primeiros)'}
                {busca.data.resultados.every((r) => r.tem_cartao === null) && ' · o Anki não abriu: sem a pista de cartão'}
              </p>
              {busca.data.resultados.map((r, i) => (
                <Verbete key={`${r.ent_seq}-${i}`} v={r} principal={i === 0} destaque={r.ent_seq === verbete} onKanji={setKanji} />
              ))}
            </div>
          )}
        </section>

        <aside className="min-w-0 space-y-6">
          <Candidatas onBuscar={buscarDeNovo} />
          <Historico onBuscar={buscarDeNovo} onKanji={setKanji} />
          <Listas onBuscar={buscarDeNovo} onKanji={setKanji} />
        </aside>
      </div>

      <FichaKanji literal={kanji} onFechar={() => setKanji(null)} />
    </div>
  )
}

/**
 * A busca, segura para o IME (DESIGN §11). Ele digita com ibus-mozc: enquanto a
 * composição está aberta o campo tem o pré-edit (かう ainda sem virar 買う), e buscar
 * isso seria buscar lixo a cada tecla. Por isso há dois textos: `texto` é o que está no
 * campo; `firme` é o texto fora da composição, e só ele vira busca, depois de uma pausa.
 * O Enter que confirma a conversão não faz nada; um Enter de verdade busca na hora.
 */
function CampoBusca({ q, buscando, onBuscar }: { q: string; buscando: boolean; onBuscar: (termo: string, confirmado: boolean) => void }) {
  const [texto, setTexto] = useState(q)
  const [firme, setFirme] = useState(q)
  const atrasado = useAtrasado(firme, 350)
  const compondo = useRef(false)
  const campo = useRef<HTMLInputElement>(null)

  // A URL mudou. Se foi o próprio campo (o atraso venceu, ou um Enter), q é o texto
  // atrasado ou o firme, e o campo fica como está: ele pode já ter digitado mais. Se não
  // bate com nenhum dos dois, veio de fora (voltar do navegador, clique no histórico) e
  // o campo acompanha.
  const [qVisto, setQVisto] = useState(q)
  if (q !== qVisto) {
    setQVisto(q)
    if (q !== firme.trim() && q !== atrasado.trim()) {
      setTexto(q)
      setFirme(q)
    }
  }

  const enviar = (t: string, confirmado: boolean) => {
    if (t !== q) onBuscar(t, confirmado)
  }

  // useEffectEvent: lê o q da hora sem fazer dele um gatilho. Se q disparasse o efeito,
  // um clique no histórico seria desfeito pelo texto velho que ainda está no atraso.
  const assentar = useEffectEvent((t: string) => enviar(t, false))
  useEffect(() => {
    assentar(atrasado.trim())
  }, [atrasado])

  const limpar = () => {
    setTexto('')
    setFirme('')
    campo.current?.focus()
  }

  return (
    <div className="relative">
      <Search className="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-muted-foreground" />
      <Input
        ref={campo}
        type="text"
        inputMode="search"
        enterKeyHint="search"
        role="searchbox"
        aria-label="Buscar no Kotoba"
        autoFocus={!q}
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        value={texto}
        placeholder="japonês, kana ou português (ex.: 持つ, たべる, comer)"
        className="h-12 rounded-xl bg-card pr-20 pl-11 text-lg md:text-lg dark:bg-card"
        onChange={(e) => {
          setTexto(e.target.value)
          if (!compondo.current && !(e.nativeEvent as InputEvent).isComposing) setFirme(e.target.value)
        }}
        onCompositionStart={() => {
          compondo.current = true
        }}
        onCompositionEnd={(e) => {
          compondo.current = false
          setFirme(e.currentTarget.value)
        }}
        onKeyDown={(e) => {
          if (enterDeVerdade(e.nativeEvent)) {
            e.preventDefault()
            setFirme(texto)
            enviar(texto.trim(), true)
          } else if (e.key === 'Escape' && texto && !emComposicao(e.nativeEvent)) {
            // Esc no meio da composição é do mozc (cancela a conversão); fora dela, limpa
            e.preventDefault()
            limpar()
          }
        }}
      />
      <div className="absolute top-1/2 right-2 flex -translate-y-1/2 items-center gap-1">
        {buscando && <Loader2 className="size-4 animate-spin text-muted-foreground" aria-label="buscando" />}
        {texto && (
          <button
            type="button"
            onClick={limpar}
            aria-label="Limpar a busca"
            className="flex size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        )}
      </div>
    </div>
  )
}

function Inicio({ onBuscar }: { onBuscar: (termo: string) => void }) {
  return (
    <div className="space-y-3 rounded-xl border border-dashed px-5 py-8 text-center">
      <p className="text-muted-foreground">
        Busque uma palavra em japonês (kanji ou kana) ou em português.
        <br className="hidden sm:inline" /> Clique num kanji da palavra para abrir a ficha dele.
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {['持つ', 'たべる', 'comer'].map((t) => (
          <button key={t} type="button" onClick={() => onBuscar(t)} className="rounded-full border bg-card px-3 py-1 hover:bg-muted">
            <TextoMisto texto={t} classeJa="text-base" />
          </button>
        ))}
      </div>
    </div>
  )
}
