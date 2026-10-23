import { ArrowRight, Check, ListChecks, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ErroCarga, Vazio } from '@/components/Estados'
import { TextoMisto } from '@/components/Ja'
import { Secao } from '@/pages/hoje/Secao'
import { useErros } from '@/api/queries'
import type { ErroRegistrado } from '@/api/types'
import { dataCurta, relativo } from '@/lib/datas'
import { cn } from '@/lib/utils'
import { plural } from '@/components/graficos/formato'

const ROTULO_BLOCO: Record<ErroRegistrado['bloco'], string> = {
  abertura: 'abertura',
  verificacao: 'verificação',
  producao: 'produção',
  diagnostico: 'diagnóstico',
  anki: 'Anki',
  outro: 'outro',
}

/** a API devolve no máximo 100 (DESIGN §6), do mais novo para o mais antigo */
const LIMITE = 100

function porDia(erros: ErroRegistrado[]) {
  const dias: { data: string; erros: ErroRegistrado[] }[] = []
  for (const e of erros) {
    const ultimo = dias[dias.length - 1]
    if (ultimo?.data === e.data) ultimo.erros.push(e)
    else dias.push({ data: e.data, erros: [e] })
  }
  return dias
}

function ItemErro({ e, onFiltrar }: { e: ErroRegistrado; onFiltrar: (c: string) => void }) {
  return (
    <li className="space-y-1.5 py-3 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge asChild variant="outline" className="font-mono text-xs">
          <button type="button" onClick={() => onFiltrar(e.categoria)} title="Filtrar por esta categoria">
            {e.categoria}
          </button>
        </Badge>
        <span className="text-xs text-muted-foreground">{ROTULO_BLOCO[e.bloco] ?? e.bloco}</span>
        {e.deslize && (
          // §9.6: errou a 1ª, acertou a 2ª depois da dica — sabe a regra, escorregou sob carga
          <Badge variant="outline" className="border-ok/40 text-xs text-ok" title="Errou a 1ª e acertou a 2ª depois da dica">
            corrigiu com a dica
          </Badge>
        )}
      </div>
      {/* Sem riscar o japonês: o traço no meio da linha come justamente o detalhe
          que errou (dakuten, ー, a perna do ん). O vermelho + ✗ já dizem "errado". */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {e.escrito !== null && (
          <span className="inline-flex items-center gap-1 rounded-md bg-erro-bg px-2 py-0.5 text-erro">
            <X className="size-3.5 shrink-0" aria-label="escreveu" />
            <span className="text-[15px]">
              <TextoMisto texto={e.escrito} classeJa="text-base" />
            </span>
          </span>
        )}
        {e.escrito !== null && e.correto !== null && <ArrowRight className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />}
        {e.correto !== null && (
          <span className="inline-flex items-center gap-1 rounded-md bg-ok-bg px-2 py-0.5 text-ok">
            <Check className="size-3.5 shrink-0" aria-label="correto" />
            <span className="text-[15px]">
              <TextoMisto texto={e.correto} classeJa="text-base" />
            </span>
          </span>
        )}
      </div>
      {e.porque && (
        <p className="text-sm leading-relaxed text-muted-foreground">
          <TextoMisto texto={e.porque} classeJa="text-[15px] text-foreground/85" />
        </p>
      )}
    </li>
  )
}

export function ListaErros({
  dias,
  filtro,
  onFiltrar,
  hoje,
}: {
  dias: number
  filtro: string
  onFiltrar: (categoria: string) => void
  hoje: string
}) {
  const q = useErros(dias, filtro)
  const n = q.data?.erros.length ?? 0

  return (
    <Secao
      titulo={
        <span id="lista-erros" className="scroll-mt-20">
          Erros corrigidos
        </span>
      }
      icone={<ListChecks />}
      acao={q.data && <span className="text-xs text-muted-foreground">{n === LIMITE ? `os ${LIMITE} mais recentes` : plural(n, 'erro', 'erros')}</span>}
    >
      <div className="space-y-4">
        {filtro && (
          <div className="flex flex-wrap items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm">
            <span className="text-muted-foreground">Filtrando por</span>
            <span className="font-mono text-[13px] font-medium">{filtro}</span>
            <Button variant="outline" size="xs" className="ml-auto" onClick={() => onFiltrar('')}>
              <X /> Limpar filtro
            </Button>
          </div>
        )}
        {q.isError ? (
          <ErroCarga erro={q.error} tentar={() => q.refetch()} />
        ) : q.isPending ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : n === 0 ? (
          <Vazio>
            {filtro
              ? `Nenhum erro de ${filtro} nos últimos ${dias} dias.`
              : `Nenhum erro registrado nos últimos ${dias} dias. Cada erro corrigido na aula aparece aqui, com o que ele escreveu, o certo e o porquê.`}
          </Vazio>
        ) : (
          <div className={cn('space-y-5 transition-opacity', q.isPlaceholderData && 'opacity-60')}>
            {porDia(q.data.erros).map((d) => (
              <section key={d.data} className="space-y-2">
                <h3 className="flex items-baseline gap-2 border-b pb-1.5 text-sm font-medium">
                  <span className="first-letter:uppercase">{dataCurta(d.data)}</span>
                  <span className="text-xs font-normal text-muted-foreground">
                    {relativo(d.data, hoje)} · {plural(d.erros.length, 'erro', 'erros')}
                  </span>
                </h3>
                <ul className="divide-y">
                  {d.erros.map((e, i) => (
                    <ItemErro key={`${d.data}-${i}`} e={e} onFiltrar={onFiltrar} />
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
      </div>
    </Secao>
  )
}
