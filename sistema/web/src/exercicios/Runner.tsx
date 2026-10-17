import { useCallback, useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { TextoMisto } from '@/components/Ja'
import { api } from '@/api/client'
import type { Correcao, Exercicio, Licao, Resultado, RespostaDe, TipoExercicio } from '@/api/types'
import { dataLonga } from '@/lib/datas'
import { cn } from '@/lib/utils'
import { ExercicioView } from './ExercicioView'
import { IconeVeredito, Resumo } from './Resumo'
import { ROTULO_BLOCO, ROTULO_TIPO } from './tipos'

type Posicao = number | 'fim'
interface Local { resultado: Resultado; contou: boolean }
interface Envio { ex: Exercicio; resposta: RespostaDe<TipoExercicio>; tempoMs: number }

const primeiraPendente = (l: Licao): Posicao => {
  const i = l.exercicios.findIndex((e) => !e.resultado)
  return i === -1 ? 'fim' : i
}

/** O executor da lição: um exercício por vez, correção na hora, resumo no fim. */
export function Runner({ licao }: { licao: Licao }) {
  const qc = useQueryClient()
  const [pos, setPos] = useState<Posicao>(() => primeiraPendente(licao))
  // o retorno do POST, mostrado na hora (antes de a lição ser relida) e nas tentativas de treino
  const [locais, setLocais] = useState<Record<number, Local>>({})
  const [praticando, setPraticando] = useState<Record<number, number>>({})

  const envio = useMutation({
    mutationFn: ({ ex, resposta, tempoMs }: Envio): Promise<Correcao> =>
      api.responder(ex.id, { resposta, tempo_ms: tempoMs }),
    onSuccess: (c, { ex, resposta }) => {
      // só a primeira resposta conta; a API diz em `contou`, e sem ela vale "não havia resultado"
      const contou = c.contou ?? ex.resultado === null
      setLocais((m) => ({ ...m, [ex.id]: { contou, resultado: { ...c, resposta, correcao: null } as Resultado } }))
      setPraticando((p) => {
        const { [ex.id]: _, ...resto } = p
        return resto
      })
      void qc.invalidateQueries({ queryKey: ['licao'] })
      void qc.invalidateQueries({ queryKey: ['licoes'] })
    },
  })

  const resultadoDe = useCallback(
    (ex: Exercicio): Resultado | null => {
      if (ex.id in praticando) return null
      const l = locais[ex.id]
      if (l && !l.contou) return l.resultado
      // o do servidor ganha: é ele que recebe a correção do tutor depois
      return ex.resultado ?? l?.resultado ?? null
    },
    [locais, praticando],
  )

  const total = licao.exercicios.length
  const feitos = licao.exercicios.filter((e) => e.resultado || locais[e.id]).length
  const ex = pos === 'fim' ? null : licao.exercicios[pos]

  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [pos])

  const irPara = (i: Posicao) => {
    envio.reset()
    setPos(i)
  }
  const proximo = () => irPara(pos === 'fim' || pos + 1 >= total ? 'fim' : pos + 1)

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
            {ex ? `${(pos as number) + 1} de ${total}` : `${feitos} de ${total} feitos`}
          </span>
        </div>
        <nav aria-label="Exercícios" className="flex flex-wrap gap-1.5">
          {licao.exercicios.map((e, i) => {
            const r = resultadoDe(e)
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
                    {r || e.resultado ? <IconeVeredito v={(r ?? e.resultado)!.veredito} className="size-4" /> : i + 1}
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  {i + 1}. {ROTULO_TIPO[e.tipo]}
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
          <ExercicioView
            // nova tentativa (treino) = widget novo, do zero
            key={`${ex.id}-${praticando[ex.id] ?? 0}`}
            ex={ex}
            resultado={resultadoDe(ex)}
            treino={!!locais[ex.id] && !locais[ex.id].contou && !(ex.id in praticando)}
            enviando={envio.isPending && envio.variables?.ex.id === ex.id}
            erroEnvio={envio.isError && envio.variables?.ex.id === ex.id ? envio.error.message : null}
            ultimo={(pos as number) + 1 >= total}
            onVerificar={(resposta, tempoMs) => envio.mutate({ ex, resposta, tempoMs })}
            onProximo={proximo}
            onPraticar={() => {
              envio.reset()
              setPraticando((p) => ({ ...p, [ex.id]: (p[ex.id] ?? 0) + 1 }))
            }}
          />
        </div>
      ) : (
        <Resumo licao={licao} resultadoDe={(id) => resultadoDe(licao.exercicios.find((e) => e.id === id)!)} irPara={irPara} />
      )}
    </div>
  )
}
