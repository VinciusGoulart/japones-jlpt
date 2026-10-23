import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowRight, Eye, Lightbulb, Loader2, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { TextoMisto } from '@/components/Ja'
import type { Exercicio, Resultado, RespostaDe, TipoExercicio } from '@/api/types'
import { emComposicao } from '@/lib/ime'
import { Feedback } from './Feedback'
import { aguardandoDica, paraWidget, respostaEmTexto } from './tipos'
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
  /** "Ver a resposta" a caminho do servidor (dica pendente, §9.6) */
  desistindo: boolean
  erroEnvio: string | null
  ultimo: boolean
  onVerificar: (resposta: QualquerResposta, tempoMs: number) => void
  onDesistir: () => void
  onProximo: () => void
  onPraticar: () => void
}

/**
 * Um exercício: enunciado, widget do tipo, Verificar → correção → Próximo.
 *
 * Com dica (§9.6, 23/10/2026): se a 1ª resposta sai errada e o tutor deixou uma dica, a correção
 * espera. A tela mostra a dica e o widget de novo em branco para a 2ª tentativa, com "Ver a
 * resposta" para desistir. Dica que faz o aluno se corrigir ensina mais que a resposta pronta.
 * O Runner remonta esta tela ao entrar e ao sair da dica, então a resposta e o tempo começam do zero.
 */
export function ExercicioView({ ex, resultado, treino, enviando, desistindo, erroEnvio, ultimo, onVerificar, onDesistir, onProximo, onPraticar }: Props) {
  const [resposta, setResposta] = useState<QualquerResposta | null>(null)
  // tempo_ms: do exercício aparecer até o Verificar
  const inicio = useRef(0)
  useEffect(() => {
    inicio.current = performance.now()
  }, [])
  const dica = aguardandoDica(resultado)
  const respondido = resultado !== null && !dica
  const podeVerificar = !respondido && resposta !== null && !enviando && !desistindo
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

        {dica && resultado && <CaixaDica dica={resultado.dica!} primeira={respostaEmTexto(ex, resultado)} />}

        <Widget ex={ex} resultado={respondido ? paraWidget(resultado) : null} onChange={onChange} />

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
              {dica && '2ª tentativa · '}
              {ex.tipo === 'producao' ? 'Enter quebra a linha · Ctrl+Enter envia' : 'Enter verifica · Enter de novo avança'}
              {ex.tipo === 'escolha' && ' · teclas 1–9 escolhem'}
            </p>
            <div className="flex flex-wrap items-center gap-3">
              {erroEnvio && <span className="text-sm text-erro">Não deu para enviar: {erroEnvio}</span>}
              {dica && (
                // data-sem-enter: com o foco aqui, o Enter clica neste botão em vez de verificar
                <Button variant="outline" size="lg" className="h-11" data-sem-enter disabled={enviando || desistindo} onClick={onDesistir}>
                  {desistindo ? <Loader2 className="animate-spin" /> : <Eye />} Ver a resposta
                </Button>
              )}
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

/** "Quase": a dica do tutor e a resposta que ele deu, para a 2ª tentativa ter onde se apoiar. */
function CaixaDica({ dica, primeira }: { dica: string; primeira: string }) {
  return (
    <div className="space-y-1.5 rounded-xl border border-aviso/40 bg-aviso-bg px-4 py-3" aria-live="polite">
      <p className="flex items-start gap-2 text-base leading-relaxed">
        <Lightbulb className="mt-1 size-4 shrink-0 text-aviso" />
        <span>
          <span className="font-medium text-aviso">Quase. Dica: </span>
          <TextoMisto texto={dica} classeJa="text-[1.1em]" />
        </span>
      </p>
      {primeira && (
        <p className="pl-6 text-sm text-muted-foreground">
          Sua resposta:{' '}
          <span className="text-foreground">
            <TextoMisto texto={primeira} classeJa="text-base" />
          </span>
        </p>
      )}
    </div>
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
    case 'explicacao':      // o Runner mostra a explicação com o ExplicacaoView: aqui nunca chega
      return null
  }
}
