import { BookOpen, Check, Hourglass, Lightbulb, X } from 'lucide-react'
import { Ja, TextoMisto } from '@/components/Ja'
import { Markdown } from '@/components/Markdown'
import type { Exercicio, Resultado } from '@/api/types'
import { cn } from '@/lib/utils'
import { respostaEmTexto } from './tipos'
import { separarGabaritoOuvir } from './widgets/gabaritoOuvir'

const VEREDITO = {
  certo: { icone: Check, texto: 'Certo', classe: 'border-ok/40 bg-ok-bg text-ok' },
  errado: { icone: X, texto: 'Errado', classe: 'border-erro/40 bg-erro-bg text-erro' },
  revisar: { icone: Hourglass, texto: 'Enviado para o tutor — a correção aparece aqui', classe: 'border-aviso/40 bg-aviso-bg text-aviso' },
}

/**
 * Depois da dica (§9.6): o placar é o da 1ª resposta (errado), mas a faixa diz o que aconteceu na 2ª.
 * Corrigir com a dica é deslize (sabe a regra, escorregou); não corrigir ou desistir é lacuna.
 */
function faixaDaDica(r: Resultado) {
  if (!r.dica || !r.segunda) return null
  if (r.autocorrigiu) return { icone: Check, texto: 'Corrigiu com a dica', nota: 'deslize · no placar conta a 1ª resposta', classe: VEREDITO.certo.classe }
  const desistiu = 'desistiu' in r.segunda
  return { icone: X, texto: desistiu ? 'Errado — você pediu a resposta' : 'Errado — nem com a dica', nota: null, classe: VEREDITO.errado.classe }
}

/** Correção na hora: veredito, gabarito e a regra — sempre reexplicada (pedido dele em 16/10). */
export function Feedback({ ex, resultado, treino }: { ex: Exercicio; resultado: Resultado; treino: boolean }) {
  const v = faixaDaDica(resultado) ?? { ...VEREDITO[resultado.veredito], nota: null }
  const Icone = v.icone
  // a 2ª tentativa está no widget; a 1ª, que é a que conta, fica registrada aqui
  const primeira = resultado.segunda && 'resposta' in resultado.segunda ? respostaEmTexto(ex, resultado) : null
  // no ordenar o widget já mostra "sua frase × gabarito"
  const mostrarGabarito = !!resultado.gabarito && ex.tipo !== 'ordenar'
  // No ouvir o gabarito é a transcrição do que a voz disse. Na compreensão ele vem
  // "texto → opção certa", e a opção certa já está marcada na lista: aqui fica só o texto.
  const ouvir = ex.tipo === 'ouvir'
  const gabarito = ouvir ? separarGabaritoOuvir(resultado.gabarito, ex.render.opcoes).dito : resultado.gabarito
  return (
    <div className="space-y-3" aria-live="polite">
      <div className={cn('flex items-center gap-2 rounded-xl border px-4 py-2.5 font-medium', v.classe)}>
        <Icone className="size-5 shrink-0" />
        <span>{v.texto}</span>
        {v.nota && <span className="text-sm font-normal opacity-80">· {v.nota}</span>}
        {resultado.correcao && resultado.veredito !== 'revisar' && <span className="text-sm font-normal opacity-80">· corrigido pelo tutor</span>}
        {treino && <span className="ml-auto text-xs font-normal opacity-80">treino — não conta no placar</span>}
      </div>

      {primeira && (
        <p className="flex flex-wrap items-baseline gap-x-2 text-sm text-muted-foreground">
          <Lightbulb className="size-3.5 shrink-0 self-center text-aviso" aria-hidden />
          <span>1ª resposta:</span>
          <span className="text-foreground">
            <TextoMisto texto={primeira} classeJa="text-base" />
          </span>
          {resultado.dica && (
            <span>
              · dica: <TextoMisto texto={resultado.dica} />
            </span>
          )}
        </p>
      )}

      {mostrarGabarito && (
        <p className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-sm text-muted-foreground">{ouvir ? 'Foi dito' : 'Gabarito'}</span>
          <Ja className="text-xl font-medium">{gabarito}</Ja>
        </p>
      )}

      {resultado.explicacao && (
        <div className="flex gap-2.5 rounded-xl bg-muted/60 px-4 py-3">
          <BookOpen className="mt-0.5 size-4 shrink-0 text-primary" />
          <p className="text-base leading-relaxed">
            <TextoMisto texto={resultado.explicacao} classeJa="text-[1.15em]" />
          </p>
        </div>
      )}

      {resultado.correcao && (
        <div className="space-y-1.5 rounded-xl border bg-card px-4 py-3">
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Correção do tutor</p>
          <Markdown texto={resultado.correcao} className="text-base" />
        </div>
      )}
    </div>
  )
}
