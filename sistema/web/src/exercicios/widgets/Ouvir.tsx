import { type MouseEvent, useCallback, useEffect, useEffectEvent, useRef, useState } from 'react'
import { AudioLines, Check, RotateCcw, RotateCw, Snail, TriangleAlert, Volume2, VolumeX, X } from 'lucide-react'
import { TextoMisto } from '@/components/Ja'
import type { DetalheTexto } from '@/api/types'
import { emComposicao } from '@/lib/ime'
import { normalizar } from '@/lib/texto'
import { cn } from '@/lib/utils'
import type { PropsWidget } from '../tipos'
import { CampoTexto, type CorrecaoTexto } from './Digitar'
import { separarGabaritoOuvir } from './gabaritoOuvir'

/** DESIGN §11: devagar = playbackRate 0,75, que o navegador toca sem mudar o tom (preservesPitch). */
const DEVAGAR = 0.75

/**
 * Autoplay: o exercício toca sozinho uma vez ao aparecer. É o caminho de menor
 * atrito (a sessão tem de caber num fim de dia de trabalho), e o clique ou o
 * Enter no "Próximo" é um gesto dele na página, o que libera o som no Chrome e no
 * Firefox. Se o navegador recusar (abriu /aula direto num ouvir), segue em
 * silêncio: o botão grande está ali. Nunca toca sozinho depois de respondido:
 * quem volta para rever o gabarito não quer levar um susto.
 *
 * A espera deixa o cartão aparecer (o Runner rola para o topo) antes da voz e,
 * no StrictMode, a montagem de ensaio é desfeita antes de o timer disparar —
 * sem ela o primeiro toque contaria dobrado.
 */
const ESPERA_AUTOPLAY_MS = 400

export function Ouvir({ render, resultado, onChange }: PropsWidget<'ouvir'>) {
  const [toques, setToques] = useState(0)
  const [texto, setTexto] = useState('')
  const [opcao, setOpcao] = useState<string | null>(null)

  // Os toques vão no corpo da resposta (§9.2): a cada toque novo a resposta é
  // reemitida, senão o Verificar mandaria a contagem da hora em que ele digitou.
  useEffect(() => {
    if (resultado) return
    if (render.modo === 'ditado') onChange(texto.trim() ? { texto, toques } : null)
    else onChange(opcao !== null ? { opcao, toques } : null)
  }, [resultado, render.modo, texto, opcao, toques, onChange])

  const contarToque = useCallback(() => setToques((n) => n + 1), [])

  const ditado = render.modo === 'ditado'
  const opcoes = render.opcoes ?? []

  // o recorte que o CampoTexto entende (a resposta do ouvir é uma união ditado | compreensão)
  const correcaoDitado: CorrecaoTexto | null =
    resultado && ditado
      ? {
          veredito: resultado.veredito,
          resposta: { texto: 'texto' in resultado.resposta ? resultado.resposta.texto : '' },
          detalhe: resultado.detalhe as Partial<DetalheTexto>,
        }
      : null

  const escolhida = resultado ? ('opcao' in resultado.resposta ? resultado.resposta.opcao : null) : opcao
  const certa = resultado && !ditado ? separarGabaritoOuvir(resultado.gabarito, opcoes).certa : null
  // revendo uma resposta: os toques que foram com ela; respondendo agora: os de agora
  const toquesMostrados = resultado ? (resultado.resposta.toques ?? null) : toques

  return (
    <div className="space-y-5">
      <Tocador
        src={render.audio}
        autoplay={!resultado}
        onToque={contarToque}
        toques={toquesMostrados}
        respondido={!!resultado}
        teclasOpcoes={!ditado && !resultado ? opcoes.length : 0}
      />
      {ditado ? (
        <CampoTexto resultado={correcaoDitado} onChange={(r) => setTexto(r?.texto ?? '')} placeholder="escreva o que ouviu (mozc)" />
      ) : (
        <Opcoes opcoes={opcoes} escolhida={escolhida} certa={certa} respondido={!!resultado} onEscolher={setOpcao} />
      )}
    </div>
  )
}

// ------------------------------------------------------------------ o tocador

type Estado = 'parado' | 'tocando' | 'falhou'

function Tocador({
  src,
  autoplay,
  onToque,
  toques,
  respondido,
  teclasOpcoes,
}: {
  src: string | null
  autoplay: boolean
  onToque: () => void
  /** null = não se sabe (resposta antiga, sem `toques`) */
  toques: number | null
  respondido: boolean
  /** quantas opções as teclas 1–N escolhem (0 = não mostrar a dica) */
  teclasOpcoes: number
}) {
  const audio = useRef<HTMLAudioElement>(null)
  const barra = useRef<HTMLDivElement>(null)
  const [estado, setEstado] = useState<Estado>('parado')
  const [devagar, setDevagar] = useState(false)
  const [jaTocou, setJaTocou] = useState(false)
  const taxa = devagar ? DEVAGAR : 1

  // Sempre do começo: a frase é curta, e "continuar de onde parou" não serve para ditado.
  const tocar = useCallback(() => {
    const a = audio.current
    if (!a) return
    a.currentTime = 0
    a.playbackRate = taxa
    if (barra.current) barra.current.style.width = '0%'
    a.play().then(
      () => {
        setJaTocou(true)
        onToque()
      },
      () => {
        /* autoplay recusado ou toque interrompido: não conta, e o botão continua ali */
      },
    )
  }, [taxa, onToque])

  // trocar a velocidade no meio vale na hora; o defaultPlaybackRate sobrevive a um load() novo
  useEffect(() => {
    const a = audio.current
    if (!a) return
    a.defaultPlaybackRate = taxa
    a.playbackRate = taxa
  }, [taxa])

  const tocarSozinho = useEffectEvent(tocar)
  useEffect(() => {
    if (!autoplay || !src) return
    const t = setTimeout(tocarSozinho, ESPERA_AUTOPLAY_MS)
    return () => clearTimeout(t)
  }, [autoplay, src])

  // Alt+R toca de novo, de qualquer lugar. Não é o Espaço nem uma letra sozinha porque
  // ele está digitando no campo do ditado; não é Ctrl+Espaço porque o ibus costuma usar
  // essa combinação para trocar de método de entrada; não é Ctrl+Enter porque é o enviar.
  // e.code (tecla física) e não e.key: com o mozc ativo o key pode vir como "Process".
  useEffect(() => {
    if (!src) return
    const onKey = (e: KeyboardEvent) => {
      if (e.code !== 'KeyR' || !e.altKey || e.ctrlKey || e.metaKey || e.shiftKey || e.repeat || emComposicao(e)) return
      e.preventDefault()
      tocar()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [src, tocar])

  // a barra anda pelo requestAnimationFrame: o timeupdate só dispara ~4 vezes por segundo e
  // numa frase de 2 s a barra pularia aos trancos. Escreve direto no estilo, sem re-render.
  useEffect(() => {
    if (estado !== 'tocando') return
    let id = 0
    const passo = () => {
      const a = audio.current
      if (a && barra.current && a.duration > 0) barra.current.style.width = `${Math.min(100, (a.currentTime / a.duration) * 100)}%`
      id = requestAnimationFrame(passo)
    }
    id = requestAnimationFrame(passo)
    return () => cancelAnimationFrame(id)
  }, [estado])

  // saiu do exercício no meio da frase: a voz não segue tocando por cima do próximo
  useEffect(() => {
    const a = audio.current
    return () => a?.pause()
  }, [])

  if (!src) {
    return (
      <div className="flex items-start gap-3 rounded-2xl border border-dashed bg-muted/30 px-4 py-3.5 text-sm">
        <VolumeX className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
        <p>
          O áudio desta frase não foi gravado. <span className="text-muted-foreground">Dá para responder mesmo assim.</span>
        </p>
      </div>
    )
  }

  const tocando = estado === 'tocando'
  // o botão não rouba o foco: no ditado o cursor continua no campo, e ele segue digitando
  const semFoco = (e: MouseEvent) => e.preventDefault()

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-3 rounded-2xl border bg-muted/40 p-4 sm:px-5">
      <audio
        ref={audio}
        src={src}
        preload="auto"
        onPlaying={() => setEstado('tocando')}
        onPause={() => setEstado((e) => (e === 'falhou' ? e : 'parado'))}
        onEnded={() => {
          setEstado('parado')
          if (barra.current) barra.current.style.width = '100%'
        }}
        onError={() => setEstado('falhou')}
        onCanPlay={() => setEstado((e) => (e === 'falhou' ? 'parado' : e))}
      />

      <button
        type="button"
        onMouseDown={semFoco}
        onClick={tocar}
        disabled={estado === 'falhou'}
        aria-label={jaTocou ? 'Ouvir de novo' : 'Ouvir'}
        className={cn(
          'relative flex size-16 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm transition-transform outline-none hover:bg-primary/90 focus-visible:ring-4 focus-visible:ring-ring/50 active:scale-95 disabled:opacity-40',
          tocando && 'ring-4 ring-primary/25',
        )}
      >
        {tocando ? (
          <AudioLines className="size-7 animate-pulse" />
        ) : jaTocou ? (
          <RotateCcw className="size-7" />
        ) : (
          <Volume2 className="size-7" />
        )}
      </button>

      <div className="min-w-0 flex-1 basis-40 space-y-2">
        {estado === 'falhou' ? (
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <TriangleAlert className="size-4 shrink-0 text-aviso" />
            <span>Não consegui carregar o áudio.</span>
            <button
              type="button"
              className="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline"
              onClick={() => {
                setEstado('parado')
                audio.current?.load()
              }}
            >
              <RotateCw className="size-3.5" /> tentar de novo
            </button>
          </p>
        ) : (
          <p className="font-medium">{tocando ? 'Tocando…' : jaTocou ? 'Ouvir de novo' : 'Ouvir'}</p>
        )}
        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <div ref={barra} className="h-full w-0 rounded-full bg-primary" />
        </div>
        <p className="flex flex-wrap gap-x-2 text-xs text-muted-foreground">
          {toques !== null && (
            <span className="tabular-nums">
              {respondido ? `ouviu ${toques}× antes de responder` : toques === 1 ? '1 toque' : `${toques} toques`}
            </span>
          )}
          <span className="hidden sm:inline">
            {toques !== null && '· '}
            <kbd className="rounded border bg-background px-1 font-sans text-[0.7rem]">Alt+R</kbd> toca de novo
            {teclasOpcoes > 0 && (
              <>
                {' · '}
                <kbd className="rounded border bg-background px-1 font-sans text-[0.7rem]">1–{teclasOpcoes}</kbd> escolhem
              </>
            )}
          </span>
        </p>
      </div>

      <div role="group" aria-label="Velocidade" className="flex shrink-0 rounded-lg border bg-background p-0.5 text-sm">
        {[
          { v: false, rotulo: 'normal' },
          { v: true, rotulo: 'devagar' },
        ].map(({ v, rotulo }) => (
          <button
            key={rotulo}
            type="button"
            onMouseDown={semFoco}
            onClick={() => setDevagar(v)}
            aria-pressed={devagar === v}
            className={cn(
              'flex items-center gap-1 rounded-md px-2.5 py-1 text-muted-foreground transition-colors hover:text-foreground',
              devagar === v && 'bg-accent font-medium text-accent-foreground',
            )}
          >
            {v && <Snail className="size-3.5" />}
            {rotulo}
          </button>
        ))}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ compreensão

/** As opções da compreensão: o mesmo desenho do Escolha, mas o texto é misto (as opções costumam ser em português). */
function Opcoes({
  opcoes,
  escolhida,
  certa,
  respondido,
  onEscolher,
}: {
  opcoes: string[]
  escolhida: string | null
  certa: string | null
  respondido: boolean
  onEscolher: (o: string) => void
}) {
  // teclas 1–9 escolhem (como no Escolha); aqui não há campo de texto para atrapalhar
  useEffect(() => {
    if (respondido) return
    const onKey = (e: KeyboardEvent) => {
      const alvo = e.target as HTMLElement | null
      if (alvo && (alvo.tagName === 'INPUT' || alvo.tagName === 'TEXTAREA')) return
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const n = Number(e.key)
      if (Number.isInteger(n) && n >= 1 && n <= opcoes.length) {
        e.preventDefault()
        onEscolher(opcoes[n - 1])
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [respondido, opcoes, onEscolher])

  return (
    <div className="grid gap-2.5" role="radiogroup">
      {opcoes.map((o, i) => {
        const marcada = escolhida === o
        const ehCerta = respondido && certa !== null && normalizar(o) === normalizar(certa)
        const errada = respondido && marcada && !ehCerta
        return (
          <button
            key={o}
            type="button"
            role="radio"
            aria-checked={marcada}
            disabled={respondido}
            onClick={() => onEscolher(o)}
            className={cn(
              'flex items-center gap-3 rounded-xl border-2 bg-card px-4 py-3 text-left transition-colors',
              !respondido && 'hover:border-primary/50 hover:bg-accent/50',
              !respondido && marcada && 'border-primary bg-accent',
              ehCerta && 'border-ok bg-ok-bg',
              errada && 'border-erro bg-erro-bg',
              respondido && !ehCerta && !errada && 'opacity-55',
              'disabled:cursor-default',
            )}
          >
            <span
              className={cn(
                'flex size-6 shrink-0 items-center justify-center rounded-md border text-xs font-medium text-muted-foreground tabular-nums',
                marcada && !respondido && 'border-primary bg-primary text-primary-foreground',
                ehCerta && 'border-ok bg-ok text-background',
                errada && 'border-erro bg-erro text-background',
              )}
            >
              {ehCerta ? <Check className="size-4" /> : errada ? <X className="size-4" /> : i + 1}
            </span>
            <span className="text-lg leading-snug">
              <TextoMisto texto={o} classeJa="text-[1.2em]" />
            </span>
            {respondido && marcada && <span className="ml-auto shrink-0 text-xs text-muted-foreground">sua resposta</span>}
          </button>
        )
      })}
    </div>
  )
}
