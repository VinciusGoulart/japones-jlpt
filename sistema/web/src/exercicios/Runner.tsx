import { useCallback, useEffect, useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Lightbulb } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { TextoMisto } from '@/components/Ja'
import { api } from '@/api/client'
import type { Correcao, Exercicio, Licao, Resultado, RespostaDe, TipoExercicio } from '@/api/types'
import { dataLonga } from '@/lib/datas'
import { cn } from '@/lib/utils'
import { ExercicioView } from './ExercicioView'
import { ExplicacaoView } from './Explicacao'
import { IconeVeredito, Resumo } from './Resumo'
import { ROTULO_BLOCO, ROTULO_TIPO, aguardandoDica, ehExercicio, numerarExercicios } from './tipos'

type Posicao = number | 'fim'
/** treino = "Praticar de novo" (não conta); senão é a 1ª resposta, ou ela com a 2ª tentativa da dica (§9.6) */
interface Local { resultado: Resultado; treino: boolean }
interface Envio { ex: Exercicio; resposta: RespostaDe<TipoExercicio>; tempoMs: number }

const primeiraPendente = (l: Licao): Posicao => {
  // a dica esperando a 2ª tentativa também é pendência: ao reabrir a lição, ele volta para ela
  let i = l.exercicios.findIndex((e) => ehExercicio(e) && (!e.resultado || aguardandoDica(e.resultado)))
  if (i === -1) return 'fim'
  // a explicação logo antes do exercício pendente aparece primeiro: é a regra que ele vai usar
  while (i > 0 && !ehExercicio(l.exercicios[i - 1])) i--
  return i
}

/** O executor da lição: um exercício por vez, correção na hora, resumo no fim. */
export function Runner({ licao }: { licao: Licao }) {
  const qc = useQueryClient()
  const [pos, setPos] = useState<Posicao>(() => primeiraPendente(licao))
  // o retorno do POST, mostrado na hora (antes de a lição ser relida) e nas tentativas de treino
  const [locais, setLocais] = useState<Record<number, Local>>({})
  const [praticando, setPraticando] = useState<Record<number, number>>({})

  const reler = () => {
    void qc.invalidateQueries({ queryKey: ['licao'] })
    void qc.invalidateQueries({ queryKey: ['licoes'] })
    void qc.invalidateQueries({ queryKey: ['regras'] })     // um exercício com regra move a agenda dela
    void qc.invalidateQueries({ queryKey: ['erros'] })      // e o deslize marca a linha do erro
  }

  // a 1ª resposta deste exercício (com a dica pendente), da tela ou do servidor, para somar a 2ª tentativa
  const primeiraDe = (m: Record<number, Local>, ex: Exercicio): Resultado | null =>
    (m[ex.id] && !m[ex.id].treino ? m[ex.id].resultado : null) ?? ex.resultado

  const envio = useMutation({
    mutationFn: ({ ex, resposta, tempoMs }: Envio): Promise<Correcao> =>
      api.responder(ex.id, { resposta, tempo_ms: tempoMs }),
    onSuccess: (c, { ex, resposta }) => {
      setLocais((m) => {
        const primeira = primeiraDe(m, ex)
        let novo: Local
        if (c.dica) {
          // 1ª errada com dica (§9.6): sem gabarito ainda, a tela pede a 2ª tentativa
          novo = { treino: false, resultado: { veredito: 'errado', resposta, gabarito: '', explicacao: null, detalhe: {}, correcao: null, dica: c.dica, segunda: null, autocorrigiu: null } }
        } else if (c.autocorrigiu !== undefined && primeira) {
          // a 2ª tentativa: o placar continua o da 1ª; a correção que chega agora é a desta
          novo = { treino: false, resultado: { ...primeira, gabarito: c.gabarito, explicacao: c.explicacao, segunda: { resposta, veredito: c.veredito, detalhe: c.detalhe }, autocorrigiu: c.autocorrigiu } }
        } else {
          // só a primeira resposta conta; a API diz em `contou`, e sem ela vale "não havia resultado"
          const contou = c.contou ?? primeira === null
          novo = { treino: !contou, resultado: { ...c, resposta, correcao: null } as Resultado }
        }
        return { ...m, [ex.id]: novo }
      })
      setPraticando((p) => {
        const { [ex.id]: _, ...resto } = p
        return resto
      })
      reler()
    },
  })

  // "Ver a resposta" com a dica pendente: é lacuna, e a correção da 1ª aparece
  const desistencia = useMutation({
    mutationFn: (ex: Exercicio): Promise<Correcao> => api.desistir(ex.id),
    onSuccess: (c, ex) => {
      setLocais((m) => {
        const primeira = primeiraDe(m, ex)
        if (!primeira) return m
        return { ...m, [ex.id]: { treino: false, resultado: { ...primeira, gabarito: c.gabarito, explicacao: c.explicacao, detalhe: c.detalhe, segunda: { desistiu: true }, autocorrigiu: false } } }
      })
      reler()
    },
  })

  const resultadoDe = useCallback(
    (ex: Exercicio): Resultado | null => {
      if (ex.id in praticando) return null
      const l = locais[ex.id]
      if (l?.treino) return l.resultado
      const s = ex.resultado
      // O do servidor ganha: é ele que recebe a correção do tutor depois. A exceção é a dica: a
      // 2ª tentativa já voltou aqui e a lição relida (ainda com a dica pendente) chega um instante depois.
      if (s && !(aguardandoDica(s) && l && !aguardandoDica(l.resultado))) return s
      return l?.resultado ?? s ?? null
    },
    [locais, praticando],
  )

  // a barra e o "N de M" contam só exercícios: a explicação não tem resposta (§9.2)
  const numero = useMemo(() => numerarExercicios(licao), [licao])
  const itens = licao.exercicios.length
  const total = numero.size
  const feitos = licao.exercicios.filter((e) => ehExercicio(e) && (e.resultado || locais[e.id])).length
  const ex = pos === 'fim' ? null : licao.exercicios[pos]

  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [pos])

  const irPara = (i: Posicao) => {
    envio.reset()
    desistencia.reset()
    setPos(i)
  }
  const proximo = () => irPara(pos === 'fim' || pos + 1 >= itens ? 'fim' : pos + 1)

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <h1 className="text-lg font-semibold">
            <TextoMisto texto={licao.titulo} classeJa="text-[1.1em]" />
          </h1>
          <p className="text-sm text-muted-foreground first-letter:uppercase">{dataLonga(licao.data)}</p>
        </div>
        <div className="flex items-center gap-3">
          <Progress value={total ? (feitos / total) * 100 : 0} className="h-2 flex-1" />
          <span className="shrink-0 text-sm text-muted-foreground tabular-nums">
            {ex ? (ehExercicio(ex) ? `${numero.get(ex.id)} de ${total}` : 'explicação') : `${feitos} de ${total} feitos`}
          </span>
        </div>
        <nav aria-label="Exercícios" className="flex flex-wrap gap-1.5">
          {licao.exercicios.map((e, i) => {
            const r = ehExercicio(e) ? resultadoDe(e) : null
            return (
              <Tooltip key={e.id}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={() => irPara(i)}
                    aria-current={pos === i ? 'step' : undefined}
                    className={cn(
                      'flex size-8 items-center justify-center rounded-lg border text-xs tabular-nums transition-colors hover:bg-muted',
                      pos === i && 'border-primary ring-2 ring-primary/30',
                    )}
                  >
                    {!ehExercicio(e) ? (
                      <BookOpen className="size-4 text-muted-foreground" aria-label="explicação" />
                    ) : aguardandoDica(r) ? (
                      <Lightbulb className="size-4 text-aviso" aria-label="dica esperando a 2ª tentativa" />
                    ) : r || e.resultado ? (
                      <IconeVeredito v={(r ?? e.resultado)!.veredito} className="size-4" />
                    ) : (
                      numero.get(e.id)
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  {ehExercicio(e) ? `${numero.get(e.id)}. ${ROTULO_TIPO[e.tipo]}` : `${ROTULO_TIPO[e.tipo]}: ${e.enunciado || e.render.titulo || ROTULO_BLOCO[e.bloco]}`}
                </TooltipContent>
              </Tooltip>
            )
          })}
          <button
            type="button"
            onClick={() => irPara('fim')}
            className={cn('rounded-lg border px-2.5 text-xs text-muted-foreground hover:bg-muted', pos === 'fim' && 'border-primary ring-2 ring-primary/30')}
          >
            resumo
          </button>
        </nav>
      </header>

      {ex ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{ROTULO_BLOCO[ex.bloco]}</Badge>
            {ROTULO_TIPO[ex.tipo] !== ROTULO_BLOCO[ex.bloco] && <Badge variant="outline">{ROTULO_TIPO[ex.tipo]}</Badge>}
          </div>
          {ex.tipo === 'explicacao' ? (
            <ExplicacaoView key={ex.id} ex={ex} ultimo={(pos as number) + 1 >= itens} onEntendi={proximo} />
          ) : (
            <ExercicioView
              // nova tentativa (treino) ou a 2ª tentativa da dica = tela nova, do zero (resposta e tempo zerados)
              key={`${ex.id}-${praticando[ex.id] ?? 0}-${aguardandoDica(resultadoDe(ex)) ? 'dica' : 'r'}`}
              ex={ex}
              resultado={resultadoDe(ex)}
              treino={!!locais[ex.id]?.treino && !(ex.id in praticando)}
              enviando={envio.isPending && envio.variables?.ex.id === ex.id}
              desistindo={desistencia.isPending && desistencia.variables?.id === ex.id}
              erroEnvio={
                envio.isError && envio.variables?.ex.id === ex.id
                  ? envio.error.message
                  : desistencia.isError && desistencia.variables?.id === ex.id
                    ? desistencia.error.message
                    : null
              }
              ultimo={(pos as number) + 1 >= itens}
              onVerificar={(resposta, tempoMs) => envio.mutate({ ex, resposta, tempoMs })}
              onDesistir={() => desistencia.mutate(ex)}
              onProximo={proximo}
              onPraticar={() => {
                envio.reset()
                setPraticando((p) => ({ ...p, [ex.id]: (p[ex.id] ?? 0) + 1 }))
              }}
            />
          )}
        </div>
      ) : (
        <Resumo licao={licao} resultadoDe={(id) => resultadoDe(licao.exercicios.find((e) => e.id === id)!)} irPara={irPara} />
      )}
    </div>
  )
}
