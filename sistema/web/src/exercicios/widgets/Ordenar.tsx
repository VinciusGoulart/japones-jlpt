import { useRef, useState } from 'react'
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, arrayMove, rectSortingStrategy, sortableKeyboardCoordinates, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Ja } from '@/components/Ja'
import { normalizar } from '@/lib/texto'
import { cn } from '@/lib/utils'
import type { PropsWidget } from '../tipos'

// As peças podem repetir (uma peça e um distrator iguais), então a identidade é o índice.
interface Peca { id: string; texto: string }

const classeChip =
  'inline-flex select-none items-center rounded-lg border-2 bg-card px-3 py-1.5 text-2xl font-ja shadow-xs transition-colors'

function ChipOrdenavel({ peca, aoClicar }: { peca: Peca; aoClicar: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: peca.id })
  return (
    <button
      ref={setNodeRef}
      type="button"
      lang="ja"
      style={{ transform: CSS.Translate.toString(transform), transition }}
      className={cn(classeChip, 'cursor-grab border-primary/40 hover:border-primary active:cursor-grabbing', isDragging && 'z-10 opacity-80 shadow-md')}
      onClick={aoClicar}
      title="Arraste para reordenar; clique para devolver ao banco"
      {...attributes}
      {...listeners}
    >
      {peca.texto}
    </button>
  )
}

export function Ordenar({ render, resultado, onChange }: PropsWidget<'ordenar'>) {
  const pecas: Peca[] = render.pecas.map((texto, i) => ({ id: `p${i}`, texto }))
  const [linha, setLinha] = useState<string[]>([])
  // o pointerup do fim de um arraste também dispara um clique na peça: ele não pode devolvê-la ao banco
  const acabouDeArrastar = useRef(false)
  const sensores = useSensors(
    // distância mínima: um clique simples devolve a peça, só um arraste de verdade reordena
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    // só Espaço pega/solta pelo teclado: o Enter é do Verificar
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
      keyboardCodes: { start: ['Space'], cancel: ['Escape'], end: ['Space'] },
    }),
  )
  const porId = new Map(pecas.map((p) => [p.id, p]))

  const mudar = (nova: string[]) => {
    setLinha(nova)
    onChange(nova.length ? { pecas: nova.map((id) => porId.get(id)!.texto) } : null)
  }

  if (resultado) {
    const montada = resultado.detalhe.montada ?? resultado.resposta.pecas.join('')
    const ok = resultado.veredito === 'certo'
    return (
      <div className="space-y-3">
        <div className={cn('flex min-h-16 flex-wrap items-center gap-2 rounded-xl border-2 p-3', ok ? 'border-ok bg-ok-bg' : 'border-erro bg-erro-bg')}>
          {resultado.resposta.pecas.map((t, i) => (
            <span key={i} lang="ja" className={classeChip}>{t}</span>
          ))}
        </div>
        <dl className="grid grid-cols-[auto_1fr] items-baseline gap-x-3 gap-y-1">
          <dt className="text-sm text-muted-foreground">Sua frase</dt>
          <dd><Ja className={cn('text-xl', ok ? 'text-ok' : 'text-erro')}>{montada || '—'}</Ja></dd>
          {!ok || normalizar(montada) !== normalizar(resultado.gabarito) ? (
            <>
              <dt className="text-sm text-muted-foreground">Gabarito</dt>
              <dd><Ja className="text-xl font-medium text-ok">{resultado.gabarito}</Ja></dd>
            </>
          ) : null}
        </dl>
      </div>
    )
  }

  const noBanco = pecas.filter((p) => !linha.includes(p.id))

  const aoSoltar = (e: DragEndEvent) => {
    acabouDeArrastar.current = true
    // o clique (se vier) chega na mesma tarefa do pointerup; depois disso a trava sai
    setTimeout(() => {
      acabouDeArrastar.current = false
    }, 0)
    if (e.over && e.active.id !== e.over.id) {
      mudar(arrayMove(linha, linha.indexOf(String(e.active.id)), linha.indexOf(String(e.over.id))))
    }
  }

  return (
    <div className="space-y-4">
      <DndContext sensors={sensores} collisionDetection={closestCenter} onDragEnd={aoSoltar}>
        <SortableContext items={linha} strategy={rectSortingStrategy}>
          <div className="flex min-h-16 flex-wrap items-center gap-2 rounded-xl border-2 border-dashed bg-muted/40 p-3">
            {linha.length === 0 && <span className="px-1 text-sm text-muted-foreground">Clique nas peças abaixo para montar a frase.</span>}
            {linha.map((id) => (
              <ChipOrdenavel
                key={id}
                peca={porId.get(id)!}
                aoClicar={() => {
                  if (acabouDeArrastar.current) return
                  mudar(linha.filter((x) => x !== id))
                }}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
      <div className="flex min-h-14 flex-wrap gap-2">
        {noBanco.map((p) => (
          <button
            key={p.id}
            type="button"
            lang="ja"
            className={cn(classeChip, 'hover:border-primary/60 hover:bg-accent')}
            onClick={() => mudar([...linha, p.id])}
          >
            {p.texto}
          </button>
        ))}
      </div>
      <p className="text-sm text-muted-foreground">Arraste as peças da linha para reordenar; clique numa delas para devolver. Pode sobrar peça.</p>
    </div>
  )
}
