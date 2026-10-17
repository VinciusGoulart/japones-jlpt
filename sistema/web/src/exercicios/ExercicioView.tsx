import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowRight, Loader2, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { TextoMisto } from '@/components/Ja'
import type { Exercicio, Resultado, RespostaDe, TipoExercicio } from '@/api/types'
import { emComposicao } from '@/lib/ime'
import { Feedback } from './Feedback'
import { Escolha } from './widgets/Escolha'
import { AcharErro } from './widgets/AcharErro'
import { Ligar } from './widgets/Ligar'
import { Ordenar } from './widgets/Ordenar'
import { Completar } from './widgets/Completar'
import { Conjugar, Digitar } from './widgets/Digitar'
import { Producao } from './widgets/Producao'
import { Ouvir } from './widgets/Ouvir'

type QualquerResposta = RespostaDe<TipoExercicio>

interface Props {
  ex: Exercicio
  /** null = ainda não respondido (ou praticando de novo) */
  resultado: Resultado | null
  treino: boolean
  enviando: boolean
  erroEnvio: string | null
  ultimo: boolean
  onVerificar: (resposta: QualquerResposta, tempoMs: number) => void
  onProximo: () => void
  onPraticar: () => void
}

/** Um exercício: enunciado, widget do tipo, Verificar → correção → Próximo. */
export function ExercicioView({ ex, resultado, treino, enviando, erroEnvio, ultimo, onVerificar, onProximo, onPraticar }: Props) {
  const [resposta, setResposta] = useState<QualquerResposta | null>(null)
  // tempo_ms: do exercício aparecer até o Verificar
  const inicio = useRef(0)
  useEffect(() => {
    inicio.current = performance.now()
  }, [])
  const respondido = resultado !== null
  const podeVerificar = !respondido && resposta !== null && !enviando
  const proximoRef = useRef<HTMLButtonElement>(null)

  const verificar = useCallback(() => {
    if (podeVerificar) onVerificar(resposta, Math.round(performance.now() - inicio.current))
  }, [podeVerificar, resposta, onVerificar])

  // Depois da correção o foco vai para o Próximo: os campos ficam desabilitados e perderiam o foco de todo jeito.
  useEffect(() => {
    if (respondido) proximoRef.current?.focus({ preventScroll: true })
  }, [respondido])

  // Enter = Verificar; com a correção na tela, Enter = Próximo.
  // NUNCA durante a composição do IME (mozc): esse Enter só confirma a conversão.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Enter' || e.defaultPrevented) return
      if (emComposicao(e) || e.repeat || e.shiftKey || e.altKey) return
      const alvo = e.target instanceof HTMLElement ? e.target : null
      if (alvo?.closest('[data-sem-enter], nav, a')) return
      // na produção o Enter quebra a linha (uma frase por linha); envia com Ctrl+Enter
      if (alvo?.tagName === 'TEXTAREA' && !(e.ctrlKey || e.metaKey)) return
      e.preventDefault()
      if (respondido) onProximo()
      else verificar()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [respondido, verificar, onProximo])

  const onChange = useCallback((r: QualquerResposta | null) => setResposta(r), [])

  return (
    <Card className="gap-6 py-6">
      <CardContent className="space-y-6 px-5 sm:px-8">
        <h2 className="text-xl leading-relaxed font-medium">
          <TextoMisto texto={ex.enunciado} classeJa="text-[1.2em]" />
        </h2>

        <Widget ex={ex} resultado={resultado} onChange={onChange} />

        {respondido ? (
          <>
            <Feedback ex={ex} resultado={resultado} treino={treino} />
            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
              {ex.tipo !== 'producao' ? (
                <Button variant="ghost" size="sm" onClick={onPraticar} className="text-muted-foreground">
                  <RotateCcw /> Praticar de novo
                </Button>
              ) : (
                <span />
              )}
              <Button ref={proximoRef} size="lg" className="h-11 px-6 text-base" onClick={onProximo}>
                {ultimo ? 'Ver o resumo' : 'Próximo'} <ArrowRight />
              </Button>
            </div>
          </>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground">
              {ex.tipo === 'producao' ? 'Enter quebra a linha · Ctrl+Enter envia' : 'Enter verifica · Enter de novo avança'}
              {ex.tipo === 'escolha' && ' · teclas 1–9 escolhem'}
            </p>
            <div className="flex items-center gap-3">
              {erroEnvio && <span className="text-sm text-erro">Não deu para enviar: {erroEnvio}</span>}
              <Button size="lg" className="h-11 px-6 text-base" disabled={!podeVerificar} onClick={verificar}>
                {enviando && <Loader2 className="animate-spin" />}
                {ex.tipo === 'producao' ? 'Enviar para o tutor' : 'Verificar'}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Widget({ ex, resultado, onChange }: { ex: Exercicio; resultado: Resultado | null; onChange: (r: QualquerResposta | null) => void }) {
  // O resultado veio do mesmo exercício, então o tipo bate; o TS só não consegue ligar as duas variáveis.
  switch (ex.tipo) {
    case 'escolha':
      return <Escolha render={ex.render} resultado={resultado as Resultado<'escolha'> | null} onChange={onChange} />
    case 'achar_erro':
      return <AcharErro render={ex.render} resultado={resultado as Resultado<'achar_erro'> | null} onChange={onChange} />
    case 'ligar':
      return <Ligar render={ex.render} resultado={resultado as Resultado<'ligar'> | null} onChange={onChange} />
    case 'ordenar':
      return <Ordenar render={ex.render} resultado={resultado as Resultado<'ordenar'> | null} onChange={onChange} />
    case 'completar':
      return <Completar render={ex.render} resultado={resultado as Resultado<'completar'> | null} onChange={onChange} />
    case 'digitar':
      return <Digitar render={ex.render} resultado={resultado as Resultado<'digitar'> | null} onChange={onChange} />
    case 'conjugar':
      return <Conjugar render={ex.render} resultado={resultado as Resultado<'conjugar'> | null} onChange={onChange} />
    case 'ouvir':
      return <Ouvir render={ex.render} resultado={resultado as Resultado<'ouvir'> | null} onChange={onChange} />
    case 'producao':
      return <Producao render={ex.render} resultado={resultado as Resultado<'producao'> | null} onChange={onChange} />
  }
}
