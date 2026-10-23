import { Link } from 'react-router'
import { BookOpen, Check, Circle, Hourglass, RotateCcw, Sun, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Ja, TextoMisto } from '@/components/Ja'
import { Markdown } from '@/components/Markdown'
import type { DetalheLigar, Exercicio, Licao, Resultado, Veredito } from '@/api/types'
import { cn } from '@/lib/utils'
import { ROTULO_BLOCO, ROTULO_TIPO, ehExercicio, numerarExercicios, respostaEmTexto } from './tipos'
import { separarGabaritoOuvir } from './widgets/gabaritoOuvir'

export function IconeVeredito({ v, className }: { v: Veredito | null; className?: string }) {
  if (v === 'certo') return <Check className={cn('text-ok', className)} aria-label="certo" />
  if (v === 'errado') return <X className={cn('text-erro', className)} aria-label="errado" />
  if (v === 'revisar') return <Hourglass className={cn('text-aviso', className)} aria-label="com o tutor" />
  return <Circle className={cn('text-muted-foreground/50', className)} aria-label="sem resposta" />
}

function Placar({ n, rotulo, classe }: { n: number; rotulo: string; classe: string }) {
  return (
    <div className={cn('rounded-xl px-4 py-3 text-center', classe)}>
      <p className="text-3xl font-semibold tabular-nums">{n}</p>
      <p className="text-sm">{rotulo}</p>
    </div>
  )
}

/** A resposta dele no resumo; nos errados, o que ele pôs riscado e o certo ao lado. */
function LinhaResposta({ ex, r }: { ex: Exercicio; r: Resultado }) {
  const errado = r.veredito === 'errado'
  const riscado = (t: string, k?: number) => (
    <Ja key={k} className="text-base text-erro line-through decoration-1">{t}</Ja>
  )
  const certo = (t: string) => <Ja className="text-base text-ok">{t}</Ja>
  const seta = <span className="text-muted-foreground">→</span>

  if (errado && ex.tipo === 'ligar') {
    // só os pares errados: a lista inteira riscada não diz onde foi o erro
    const pares = (r.detalhe as Partial<DetalheLigar>).pares?.filter((p) => !p.ok) ?? []
    return (
      <ul className="space-y-0.5 text-sm">
        {pares.map((p) => (
          <li key={p.esquerda} className="flex flex-wrap items-baseline gap-x-2">
            <Ja className="text-base">{p.esquerda}</Ja>
            <span className="text-muted-foreground">—</span>
            {p.escolhida && riscado(p.escolhida)}
            {seta}
            {certo(p.certa)}
          </li>
        ))}
      </ul>
    )
  }
  if (ex.tipo === 'producao') {
    const frases = (r.resposta as { frases?: string[] }).frases ?? []
    return (
      <ol className="list-decimal space-y-0.5 pl-5 text-sm marker:text-muted-foreground">
        {frases.map((f, i) => (
          <li key={i}><Ja className="text-base">{f}</Ja></li>
        ))}
      </ol>
    )
  }
  if (ex.tipo === 'ouvir' && ex.render.modo === 'escolha') {
    // a resposta e a opção certa são frases (em geral em português): sem lang="ja", e o
    // que a voz disse vai ao lado, porque sem ele a linha não diz o que foi ouvido
    const { dito, certa } = separarGabaritoOuvir(r.gabarito, ex.render.opcoes)
    return (
      <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
        <span className={cn(errado && 'text-erro line-through decoration-1')}>
          <TextoMisto texto={respostaEmTexto(ex, r) || '—'} classeJa="text-base" />
        </span>
        {errado && certa && (
          <>
            {seta}
            <span className="text-ok">
              <TextoMisto texto={certa} classeJa="text-base" />
            </span>
          </>
        )}
        {dito && (
          <span className="text-muted-foreground">
            · foi dito <Ja className="text-base text-foreground">{dito}</Ja>
          </span>
        )}
      </p>
    )
  }
  if (errado && ex.tipo === 'achar_erro') {
    return (
      <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
        <span className="text-muted-foreground">marcou</span>
        {riscado(respostaEmTexto(ex, r))}
        <span className="text-muted-foreground">· o erro era</span>
        {certo(r.gabarito)}
      </p>
    )
  }
  return (
    <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
      {errado ? riscado(respostaEmTexto(ex, r) || '—') : <Ja className="text-base">{respostaEmTexto(ex, r) || '—'}</Ja>}
      {errado && r.gabarito && (
        <>
          {seta}
          {certo(r.gabarito)}
        </>
      )}
    </p>
  )
}

/** Tela do fim: placar e a lista com ✓/✗/⏳; a produção mostra a correção do tutor quando chega. */
export function Resumo({
  licao,
  resultadoDe,
  irPara,
}: {
  licao: Licao
  resultadoDe: (id: number) => Resultado | null
  irPara: (indice: number) => void
}) {
  // a explicação não tem resposta: fica fora do placar e dos pendentes (§9.2)
  const rs = licao.exercicios.map((e) => (ehExercicio(e) ? resultadoDe(e.id) : null))
  const conta = (v: Veredito) => rs.filter((r) => r?.veredito === v).length
  const pendentes = licao.exercicios.filter((e, i) => ehExercicio(e) && !rs[i]).length
  const numero = numerarExercicios(licao)
  const esperando = conta('revisar')

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-3">
        <Placar n={conta('certo')} rotulo="certos" classe="bg-ok-bg text-ok" />
        <Placar n={conta('errado')} rotulo="errados" classe="bg-erro-bg text-erro" />
        <Placar n={esperando} rotulo="com o tutor" classe="bg-aviso-bg text-aviso" />
      </div>
      {pendentes > 0 && (
        <p className="text-sm text-muted-foreground">
          {pendentes} exercício{pendentes > 1 ? 's' : ''} sem resposta — clique para fazer.
        </p>
      )}
      {esperando > 0 && (
        <p className="text-sm text-muted-foreground">
          {/* não é só a produção: um ditado fora das aceitas também vai para o tutor */}
          {esperando > 1 ? `${esperando} exercícios foram` : '1 exercício foi'} para o tutor; a correção aparece aqui sozinha (a página confere
          a cada 20 s).
        </p>
      )}

      <Card className="py-0">
        <CardContent className="divide-y px-0">
          {licao.exercicios.map((ex, i) => {
            if (ex.tipo === 'explicacao')
              return (
                <div key={ex.id} className="px-5 py-3">
                  <button type="button" onClick={() => irPara(i)} className="flex w-full items-start gap-3 text-left hover:opacity-80">
                    <BookOpen className="mt-1 size-5 shrink-0 text-muted-foreground" aria-hidden />
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <p className="text-xs text-muted-foreground">{ROTULO_TIPO[ex.tipo]} · rever</p>
                      <p className="truncate text-sm">
                        <TextoMisto texto={ex.enunciado || ex.render.titulo || ROTULO_BLOCO[ex.bloco]} />
                      </p>
                    </div>
                  </button>
                </div>
              )
            const r = rs[i]
            return (
              <div key={ex.id} className="space-y-2 px-5 py-3.5">
                <button type="button" onClick={() => irPara(i)} className="flex w-full items-start gap-3 text-left hover:opacity-80">
                  <IconeVeredito v={r?.veredito ?? null} className="mt-1 size-5 shrink-0" />
                  <div className="min-w-0 flex-1 space-y-0.5">
                    <p className="text-xs text-muted-foreground">
                      {numero.get(ex.id)}. {ROTULO_TIPO[ex.tipo]}
                    </p>
                    <p className="truncate text-sm">
                      <TextoMisto texto={ex.enunciado} />
                    </p>
                    {r && <LinhaResposta ex={ex} r={r} />}
                  </div>
                </button>
                {r?.correcao && (
                  <div className="ml-8 rounded-lg bg-muted/60 px-3 py-2">
                    <p className="mb-1 text-xs font-medium text-muted-foreground">Correção do tutor</p>
                    <Markdown texto={r.correcao} className="text-sm" />
                  </div>
                )}
                {r?.veredito === 'revisar' && !r.correcao && (
                  <p className="ml-8 text-xs text-aviso">aguardando a correção do tutor…</p>
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>

      <div className="flex flex-wrap justify-between gap-3">
        <Button variant="outline" onClick={() => irPara(0)}>
          <RotateCcw /> Rever do começo
        </Button>
        <Button asChild>
          <Link to="/">
            <Sun /> Voltar para Hoje
          </Link>
        </Button>
      </div>
    </div>
  )
}
