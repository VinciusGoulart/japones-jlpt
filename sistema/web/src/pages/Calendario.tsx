import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin, { type DateClickArg } from '@fullcalendar/interaction'
import ptBrLocale from '@fullcalendar/core/locales/pt-br'
import type { DatesSetArg, DayCellContentArg, EventClickArg, EventInput } from '@fullcalendar/core'
import { Headphones, Loader2 } from 'lucide-react'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga, FonteFora } from '@/components/Estados'
import { useCalendario } from '@/api/queries'
import { ehErro, type DiaCalendario, type EventoTrello } from '@/api/types'
import { dataCompleta, diaDeEstudoLocal, paraIso, somarDias } from '@/lib/datas'
import { semMarkdown } from '@/lib/texto'
import { DiaDetalhe } from './calendario/DiaDetalhe'
import { tipoDoDia } from './calendario/tipos'

// fora do componente: o FullCalendar compara opções por referência e re-renderiza ao mudar
const PLUGINS = [dayGridPlugin, interactionPlugin]
const BARRA = { left: 'title', center: '', right: 'today prev,next' }

export function PaginaCalendario() {
  const navegar = useNavigate()
  const [faixa, setFaixa] = useState<{ de: string; ate: string } | null>(null)
  const [aberto, setAberto] = useState<string | null>(null)
  const q = useCalendario(faixa?.de ?? null, faixa?.ate ?? null)

  const porData = useMemo(() => new Map((q.data?.dias ?? []).map((d) => [d.data, d])), [q.data])
  const trello = useMemo<EventoTrello[]>(
    () => (q.data && !ehErro(q.data.eventos_trello) ? q.data.eventos_trello : []),
    [q.data],
  )

  const eventos = useMemo<EventInput[]>(() => {
    const ev: EventInput[] = []
    for (const d of q.data?.dias ?? []) {
      if (d.plano) ev.push({ title: semMarkdown(d.plano), start: d.data, allDay: true, classNames: ['ev-plano'], extendedProps: { tipo: 'plano', ordem: 0 } })
      for (const l of d.licoes)
        ev.push({ title: `✎ ${l.titulo}`, start: d.data, allDay: true, url: `/aula/${l.id}`, classNames: ['ev-licao'], extendedProps: { tipo: 'licao', ordem: 1 } })
    }
    for (const t of trello)
      ev.push({
        title: t.nome, start: t.vence, allDay: true, url: t.url ?? undefined,
        classNames: ['ev-trello', ...(t.concluido ? ['ev-concluido'] : [])],
        extendedProps: { tipo: 'trello', ordem: 2 },
      })
    return ev
  }, [q.data, trello])

  const aoMudarDatas = (arg: DatesSetArg) => {
    // o fim do FullCalendar é exclusivo; a API quer o último dia incluído
    const de = paraIso(arg.start)
    const ate = paraIso(somarDias(arg.end, -1))
    setFaixa((f) => (f?.de === de && f.ate === ate ? f : { de, ate }))
  }

  const aoClicarEvento = (arg: EventClickArg) => {
    arg.jsEvent.preventDefault()
    const tipo = arg.event.extendedProps.tipo as string
    if (tipo === 'licao' && arg.event.url) navegar(arg.event.url)
    else if (tipo === 'trello' && arg.event.url) window.open(arg.event.url, '_blank', 'noopener')
    else if (arg.event.start) setAberto(paraIso(arg.event.start))
  }

  const conteudoDoDia = useCallback(
    (arg: DayCellContentArg) => {
      const d = porData.get(paraIso(arg.date))
      return (
        <span className="flex items-center gap-1">
          {d?.trajeto?.audio === 1 && <Headphones className="size-3 text-primary" aria-label="áudio feito" />}
          {arg.dayNumberText}
        </span>
      )
    },
    [porData],
  )

  const classesDoDia = useCallback(
    (arg: DayCellContentArg) => {
      const iso = paraIso(arg.date)
      const tipo = tipoDoDia(porData.get(iso))
      return [tipo ? `dia-${tipo}` : '', iso === aberto ? 'dia-selecionado' : ''].filter(Boolean)
    },
    [porData, aberto],
  )

  // o "hoje" do calendário segue o dia de estudo (vira às 04:00), como o resto do sistema
  const agora = useMemo(() => diaDeEstudoLocal(), [])

  const diaAberto: DiaCalendario | undefined = aberto ? porData.get(aberto) : undefined

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Calendário</h1>
        {q.isFetching && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
      </div>
      {q.isError && <ErroCarga erro={q.error} tentar={() => q.refetch()} />}
      {q.data && ehErro(q.data.eventos_trello) && <FonteFora nome="Trello" erro={q.data.eventos_trello.erro} />}

      <div className="calendario relative rounded-xl border bg-card p-3 sm:p-4">
        {!q.data && q.isPending && faixa && <Skeleton className="absolute inset-x-4 top-16 bottom-4 z-10 rounded-lg opacity-60" />}
        <FullCalendar
          plugins={PLUGINS}
          initialView="dayGridMonth"
          locale={ptBrLocale}
          firstDay={1}
          now={agora}
          height="auto"
          fixedWeekCount={false}
          headerToolbar={BARRA}
          dayMaxEvents={3}
          events={eventos}
          eventOrder="ordem"
          datesSet={aoMudarDatas}
          dateClick={(arg: DateClickArg) => setAberto(arg.dateStr)}
          eventClick={aoClicarEvento}
          dayCellContent={conteudoDoDia}
          dayCellClassNames={classesDoDia}
        />
      </div>

      <Legenda />

      <Sheet open={!!aberto} onOpenChange={(o) => !o && setAberto(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-md">
          <SheetHeader>
            <SheetTitle className="first-letter:uppercase">{aberto ? dataCompleta(aberto) : ''}</SheetTitle>
            <SheetDescription>Mesa, trajeto, plano, lições e prazos do dia.</SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-6">
            {aberto && <DiaDetalhe dia={diaAberto} trello={trello.filter((t) => t.vence === aberto)} />}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}

function Legenda() {
  const item = (cor: string, rotulo: string) => (
    <span className="flex items-center gap-1.5">
      <span className={`inline-block size-3 rounded-sm ${cor}`} />
      {rotulo}
    </span>
  )
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground">
      {item('bg-ok/35', 'aula completa')}
      {item('bg-aviso/40', 'parcial')}
      {item('bg-erro/30', 'sem mesa')}
      <span className="flex items-center gap-1.5">
        <Headphones className="size-3 text-primary" /> áudio feito
      </span>
      {item('bg-licao-bg ring-1 ring-licao/40', 'lição')}
      {item('bg-trello-bg ring-1 ring-trello/40', 'prazo do Trello')}
      <span className="flex items-center gap-1.5 italic">plano do dia</span>
    </div>
  )
}
