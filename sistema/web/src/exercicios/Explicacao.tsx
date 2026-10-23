import { useEffect, useRef } from 'react'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { TextoMisto } from '@/components/Ja'
import { Markdown } from '@/components/Markdown'
import type { ExercicioDe } from '@/api/types'
import { emComposicao } from '@/lib/ime'

/**
 * O texto do conteúdo novo, antes dos exercícios (23/10/2026, pedido dele): a regra
 * explicada no painel, onde ele vai usá-la, e não só no terminal. Não tem resposta:
 * o "Entendi" só avança. O markdown passa pelo mesmo `Markdown` das correções
 * (react-markdown, sem HTML cru), com tabelas, listas e negrito.
 */
export function ExplicacaoView({ ex, ultimo, onEntendi }: { ex: ExercicioDe<'explicacao'>; ultimo: boolean; onEntendi: () => void }) {
  const botao = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    botao.current?.focus({ preventScroll: true })
  }, [])

  // Enter = Entendi, com a mesma regra do ExercicioView: nunca durante a composição do IME.
  // O preventDefault impede o clique nativo do botão focado: sem ele, o Enter avançaria dois.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Enter' || e.defaultPrevented) return
      if (emComposicao(e) || e.repeat || e.shiftKey || e.altKey) return
      const alvo = e.target instanceof HTMLElement ? e.target : null
      if (alvo?.closest('[data-sem-enter], nav, a')) return
      e.preventDefault()
      onEntendi()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onEntendi])

  const titulo = ex.enunciado || ex.render.titulo
  return (
    <Card className="gap-6 py-6">
      <CardContent className="space-y-6 px-5 sm:px-8">
        {titulo && (
          <h2 className="text-xl leading-relaxed font-medium">
            <TextoMisto texto={titulo} classeJa="text-[1.2em]" />
          </h2>
        )}
        <Markdown texto={ex.render.md} className="text-[1.05rem]" />
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <p className="text-xs text-muted-foreground">Enter avança</p>
          <Button ref={botao} size="lg" className="h-11 px-6 text-base" onClick={onEntendi}>
            {ultimo ? 'Entendi — ver o resumo' : 'Entendi'} <ArrowRight />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
