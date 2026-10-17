import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Ja } from '@/components/Ja'
import type { ParLigar } from '@/api/types'
import { cn } from '@/lib/utils'
import type { PropsWidget } from '../tipos'

type Lado = 'e' | 'd'
interface Linha { x1: number; y1: number; x2: number; y2: number; tipo: 'par' | 'ok' | 'erro' | 'certa' }

export function Ligar({ render, resultado, onChange }: PropsWidget<'ligar'>) {
  // esquerda → direita
  const [pares, setPares] = useState<Map<string, string>>(new Map())
  const [sel, setSel] = useState<{ lado: Lado; valor: string } | null>(null)
  const caixa = useRef<HTMLDivElement>(null)
  const itens = useRef(new Map<string, HTMLElement>())
  const [linhas, setLinhas] = useState<Linha[]>([])

  const atuais = useMemo<Map<string, string>>(() => (resultado ? new Map(resultado.resposta.pares) : pares), [resultado, pares])
  const detalhe = useMemo(
    () => new Map<string, ParLigar>((resultado?.detalhe.pares ?? []).map((p) => [p.esquerda, p])),
    [resultado],
  )
  const ladoDireitoDe = new Map([...atuais].map(([e, d]) => [d, e]))

  const atualizar = (novo: Map<string, string>) => {
    setPares(novo)
    const completo = render.esquerda.every((e) => novo.has(e))
    onChange(completo ? { pares: render.esquerda.map((e) => [e, novo.get(e)!] as [string, string]) } : null)
  }

  const clicar = (lado: Lado, valor: string) => {
    if (resultado) return
    // clicar num item já ligado desfaz o par
    const parDe = lado === 'e' ? (pares.has(valor) ? valor : null) : ladoDireitoDe.get(valor) ?? null
    if (parDe !== null) {
      const novo = new Map(pares)
      novo.delete(parDe)
      setSel(null)
      atualizar(novo)
      return
    }
    if (!sel || sel.lado === lado) {
      setSel(sel?.valor === valor ? null : { lado, valor })
      return
    }
    const [e, d] = lado === 'e' ? [valor, sel.valor] : [sel.valor, valor]
    setSel(null)
    atualizar(new Map(pares).set(e, d))
  }

  // As linhas são desenhadas por cima, ligando a borda direita do item da
  // esquerda à borda esquerda do da direita; recalculadas em todo resize.
  const medir = useCallback(() => {
    const c = caixa.current
    if (!c) return
    const base = c.getBoundingClientRect()
    const ponto = (lado: Lado, v: string) => {
      const r = itens.current.get(`${lado}:${v}`)?.getBoundingClientRect()
      if (!r) return null
      return { x: (lado === 'e' ? r.right : r.left) - base.left, y: r.top + r.height / 2 - base.top }
    }
    const novas: Linha[] = []
    for (const [e, d] of atuais) {
      const a = ponto('e', e)
      const b = ponto('d', d)
      if (!a || !b) continue
      const det = detalhe.get(e)
      novas.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y, tipo: !det ? 'par' : det.ok ? 'ok' : 'erro' })
      if (det && !det.ok) {
        const c2 = ponto('d', det.certa)
        if (c2) novas.push({ x1: a.x, y1: a.y, x2: c2.x, y2: c2.y, tipo: 'certa' })
      }
    }
    setLinhas(novas)
  }, [atuais, detalhe])

  useLayoutEffect(() => {
    medir()
    const c = caixa.current
    if (!c) return
    const obs = new ResizeObserver(medir)
    obs.observe(c)
    window.addEventListener('resize', medir)
    // a fonte japonesa chega depois e muda a altura dos itens
    void document.fonts?.ready.then(medir)
    return () => {
      obs.disconnect()
      window.removeEventListener('resize', medir)
    }
  }, [medir])

  const item = (lado: Lado, v: string) => {
    const ligado = lado === 'e' ? atuais.has(v) : ladoDireitoDe.has(v)
    const det = lado === 'e' ? detalhe.get(v) : detalhe.get(ladoDireitoDe.get(v) ?? '')
    const selecionado = sel?.lado === lado && sel.valor === v
    return (
      <button
        key={v}
        ref={(el) => {
          if (el) itens.current.set(`${lado}:${v}`, el)
          else itens.current.delete(`${lado}:${v}`)
        }}
        type="button"
        disabled={!!resultado}
        onClick={() => clicar(lado, v)}
        aria-pressed={selecionado}
        title={ligado && !resultado ? 'Clique para desfazer o par' : undefined}
        className={cn(
          'relative z-10 w-full rounded-xl border-2 bg-card px-4 py-2.5 text-center transition-colors disabled:cursor-default',
          !resultado && 'hover:border-primary/50',
          selecionado && 'border-primary bg-accent ring-3 ring-primary/25',
          ligado && !resultado && 'border-primary/60',
          det && (det.ok ? 'border-ok bg-ok-bg' : 'border-erro bg-erro-bg'),
        )}
      >
        <Ja className="text-2xl">{v}</Ja>
      </button>
    )
  }

  const cor: Record<Linha['tipo'], string> = {
    par: 'var(--primary)',
    ok: 'var(--ok)',
    erro: 'var(--erro)',
    certa: 'var(--ok)',
  }

  return (
    <div className="space-y-4">
      <div ref={caixa} className="relative mx-auto grid max-w-2xl grid-cols-[minmax(0,15rem)_minmax(3rem,1fr)_minmax(0,15rem)] gap-y-3">
        <svg className="pointer-events-none absolute inset-0 size-full overflow-visible" aria-hidden>
          {linhas.map((l, i) => (
            <g key={i}>
              <line
                x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2}
                stroke={cor[l.tipo]}
                strokeWidth={l.tipo === 'certa' ? 2 : 2.5}
                strokeDasharray={l.tipo === 'certa' ? '6 5' : undefined}
                strokeLinecap="round"
              />
              <circle cx={l.x1} cy={l.y1} r={4} fill={cor[l.tipo]} />
              <circle cx={l.x2} cy={l.y2} r={4} fill={cor[l.tipo]} />
            </g>
          ))}
        </svg>
        <div className="col-start-1 flex flex-col gap-3">{render.esquerda.map((v) => item('e', v))}</div>
        <div className="col-start-3 flex flex-col gap-3">{render.direita.map((v) => item('d', v))}</div>
      </div>
      {!resultado && (
        <p className="text-sm text-muted-foreground">
          Clique num item de um lado e depois no par do outro. Clique num item ligado para desfazer.
        </p>
      )}
      {resultado && detalhe.size > 0 && [...detalhe.values()].some((p) => !p.ok) && (
        <ul className="space-y-1 text-sm">
          {[...detalhe.values()].filter((p) => !p.ok).map((p) => (
            <li key={p.esquerda} className="flex flex-wrap items-baseline gap-x-2">
              <Ja className="text-lg">{p.esquerda}</Ja>
              <span className="text-muted-foreground">→</span>
              <Ja className="text-lg font-medium text-ok">{p.certa}</Ja>
              {p.escolhida && (
                <span className="text-muted-foreground">
                  (você ligou <Ja className="text-erro line-through">{p.escolhida}</Ja>)
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
