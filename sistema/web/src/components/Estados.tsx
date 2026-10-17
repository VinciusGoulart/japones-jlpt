import type { ReactNode } from 'react'
import { TriangleAlert, CloudOff, RotateCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErroApi } from '@/api/client'
import { cn } from '@/lib/utils'

/** Uma fonte externa (Trello, Anki) fora do ar: aviso discreto, o resto da tela segue. */
export function FonteFora({ nome, erro, className }: { nome: string; erro: string; className?: string }) {
  return (
    <p className={cn('flex items-start gap-2 rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground', className)}>
      <CloudOff className="mt-0.5 size-4 shrink-0" />
      <span>
        {nome} indisponível agora <span className="opacity-70">— {erro}</span>
      </span>
    </p>
  )
}

/** Falha ao carregar uma tela inteira. */
export function ErroCarga({ erro, tentar }: { erro: unknown; tentar?: () => void }) {
  const msg = erro instanceof ErroApi || erro instanceof Error ? erro.message : String(erro)
  return (
    <div className="flex flex-col items-start gap-3 rounded-xl border border-erro/30 bg-erro-bg p-4 text-sm">
      <p className="flex items-center gap-2 font-medium text-erro">
        <TriangleAlert className="size-4" /> Não deu para carregar
      </p>
      <p className="text-foreground/80">{msg}</p>
      {tentar && (
        <Button variant="outline" size="sm" onClick={tentar}>
          <RotateCw /> Tentar de novo
        </Button>
      )}
    </div>
  )
}

export function Vazio({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">{children}</p>
}
