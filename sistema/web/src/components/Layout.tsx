import { NavLink, Outlet } from 'react-router'
import { BookOpenText, CalendarDays, Layers, NotebookPen, Search, Sun, TriangleAlert } from 'lucide-react'
import { MOCK } from '@/api/client'
import { cn } from '@/lib/utils'
import { Ja } from './Ja'

const itens = [
  { para: '/', rotulo: 'Hoje', icone: Sun, fim: true },
  { para: '/aula', rotulo: 'Aula', icone: NotebookPen, fim: false },
  { para: '/calendario', rotulo: 'Calendário', icone: CalendarDays, fim: false },
  { para: '/aulas', rotulo: 'Aulas', icone: BookOpenText, fim: false },
  { para: '/erros', rotulo: 'Erros', icone: TriangleAlert, fim: false },
  { para: '/anki', rotulo: 'Anki', icone: Layers, fim: false },
  { para: '/kotoba', rotulo: 'Kotoba', icone: Search, fim: false },
]

export function Layout() {
  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur supports-backdrop-filter:bg-background/70">
        <nav className="mx-auto flex h-14 max-w-6xl items-center gap-0.5 px-3 sm:gap-1 sm:px-4" aria-label="Principal">
          <NavLink to="/" className="mr-1 flex shrink-0 items-baseline gap-2 font-semibold tracking-tight whitespace-nowrap sm:mr-4">
            <Ja className="text-lg">日本語</Ja>
            <span className="hidden text-sm text-muted-foreground sm:inline">estudo</span>
          </NavLink>
          {itens.map(({ para, rotulo, icone: Icone, fim }) => (
            <NavLink
              key={para}
              to={para}
              end={fim}
              // no celular só o ícone aparece: o nome fica para o leitor de tela e para o tooltip
              aria-label={rotulo}
              title={rotulo}
              className={({ isActive }) =>
                cn(
                  'flex shrink-0 items-center gap-1.5 rounded-md px-2 py-1.5 text-sm sm:px-3 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                  isActive && 'bg-accent font-medium text-accent-foreground',
                )
              }
            >
              <Icone className="size-4" />
              <span className="hidden sm:inline">{rotulo}</span>
            </NavLink>
          ))}
          {MOCK && (
            <span className="ml-auto hidden rounded bg-aviso-bg px-2 py-0.5 text-xs font-medium text-aviso sm:inline">dados de exemplo</span>
          )}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  )
}
