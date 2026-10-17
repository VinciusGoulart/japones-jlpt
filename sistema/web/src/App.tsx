import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router'
import { Layout } from '@/components/Layout'
import { PaginaHoje } from '@/pages/Hoje'
import { Vazio } from '@/components/Estados'
import { Skeleton } from '@/components/ui/skeleton'

// o FullCalendar e o executor de exercícios ficam em pedaços separados: a tela Hoje abre mais leve
const PaginaAula = lazy(() => import('@/pages/Aula').then((m) => ({ default: m.PaginaAula })))
const PaginaCalendario = lazy(() => import('@/pages/Calendario').then((m) => ({ default: m.PaginaCalendario })))
const PaginaAulas = lazy(() => import('@/pages/Aulas').then((m) => ({ default: m.PaginaAulas })))
const PaginaAulaDia = lazy(() => import('@/pages/AulaDia').then((m) => ({ default: m.PaginaAulaDia })))
// Fase 3: os gráficos (Recharts) só carregam nas telas que os usam
const PaginaErros = lazy(() => import('@/pages/Erros').then((m) => ({ default: m.PaginaErros })))
const PaginaAnki = lazy(() => import('@/pages/Anki').then((m) => ({ default: m.PaginaAnki })))
const PaginaKotoba = lazy(() => import('@/pages/Kotoba').then((m) => ({ default: m.PaginaKotoba })))

const carregando = <Skeleton className="h-96 rounded-xl" />

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={carregando}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<PaginaHoje />} />
            <Route path="aula" element={<PaginaAula />} />
            <Route path="aula/:id" element={<PaginaAula />} />
            <Route path="calendario" element={<PaginaCalendario />} />
            <Route path="aulas" element={<PaginaAulas />} />
            <Route path="aulas/:data" element={<PaginaAulaDia />} />
            <Route path="erros" element={<PaginaErros />} />
            <Route path="anki" element={<PaginaAnki />} />
            <Route path="kotoba" element={<PaginaKotoba />} />
            <Route path="*" element={<Vazio>Página não encontrada.</Vazio>} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
