import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ErroApi } from '@/api/client'
import { instalarRastreioIme } from '@/lib/ime'
import App from './App'
import './index.css'

instalarRastreioIme()

const cliente = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // 404 é resposta, não falha de rede: não adianta repetir
      retry: (n, erro) => !(erro instanceof ErroApi && erro.status >= 400 && erro.status < 500) && n < 2,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={cliente}>
      <TooltipProvider delayDuration={300}>
        <App />
      </TooltipProvider>
    </QueryClientProvider>
  </StrictMode>,
)
