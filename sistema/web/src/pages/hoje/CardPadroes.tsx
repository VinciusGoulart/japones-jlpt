import { Eye } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Vazio } from '@/components/Estados'
import { TextoMisto } from '@/components/Ja'
import type { PadraoAberto } from '@/api/types'
import { ddmm } from '@/lib/datas'
import { Secao } from './Secao'

export function CardPadroes({ padroes }: { padroes: PadraoAberto[] }) {
  return (
    <Secao titulo="Padrões em vigília" icone={<Eye />}>
      {padroes.length === 0 ? (
        <Vazio>Nenhum padrão aberto.</Vazio>
      ) : (
        <ul className="divide-y">
          {padroes.map((p) => (
            <li key={p.id} className="space-y-1 py-2.5 first:pt-0 last:pb-0">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="font-mono text-xs">{p.categoria}</Badge>
                <span className="text-xs text-muted-foreground">desde {ddmm(p.aberto_em)}</span>
              </div>
              <p className="text-sm leading-relaxed">
                <TextoMisto texto={p.descricao} classeJa="text-base" />
              </p>
            </li>
          ))}
        </ul>
      )}
    </Secao>
  )
}
