import { NavLink, Outlet } from 'react-router'
import { BookOpenText, CalendarDays, NotebookPen, Sun } from 'lucide-react'
import { MOCK } from '@/api/client'
import { cn } from '@/lib/utils'
import { Ja } from './Ja'

const itens = [
  { para: '/', rotulo: 'Hoje', icone: Sun, fim: true },
  { para: '/aula', rotulo: 'Aula', icone: NotebookPen, fim: false },
  { para: '/calendario', rotulo: 'Calendário', icone: CalendarDays, fim: false },
  { para: '/aulas', rotulo: 'Aulas', icone: BookOpenText, fim: false },
]

export function Layout() {
  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur supports-backdrop-filter:bg-background/70">
        <nav className="mx-auto flex h-14 max-w-6xl items-center gap-1 px-4" aria-label="Principal">
          <NavLink to="/" className="mr-4 flex items-baseline gap-2 font-semibold tracking-tight">
            <Ja className="text-lg">日本語</Ja>
            <span className="hidden text-sm text-muted-foreground sm:inline">estudo</span>
          </NavLink>
          {itens.map(({ para, rotulo, icone: Icone, fim }) => (
            <NavLink
              key={para}
              to={para}
              end={fim}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                  isActive && 'bg-accent font-medium text-accent-foreground',
                )
              }
            >
              <Icone className="size-4" />
              <span className="hidden sm:inline">{rotulo}</span>
            </NavLink>
          ))}
          {MOCK && (
            <span className="ml-auto rounded bg-aviso-bg px-2 py-0.5 text-xs font-medium text-aviso">dados de exemplo</span>
          )}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  )
}
