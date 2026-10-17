import { CircleCheck, Eye } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Vazio } from '@/components/Estados'
import { TextoMisto } from '@/components/Ja'
import { Secao } from '@/pages/hoje/Secao'
import type { ErrosPainel, Padrao } from '@/api/types'
import { ddmm, diasEntre } from '@/lib/datas'
import { plural } from '@/components/graficos/formato'

function BotaoCategoria({ categoria, onFiltrar }: { categoria: string; onFiltrar: (c: string) => void }) {
  return (
    <Badge asChild variant="outline" className="font-mono text-xs">
      <button type="button" onClick={() => onFiltrar(categoria)} title="Ver os erros desta categoria">
        {categoria}
      </button>
    </Badge>
  )
}

/**
 * Padrões em vigília (o "topo de pontos_fracos"). Cada aberto mostra há quanto
 * tempo está aberto e quantos erros da categoria caíram no período: um padrão
 * aberto há semanas e ainda com erro é o que pede outra abordagem na aula.
 */
export function Padroes({
  padroes,
  porCategoria,
  dias,
  desde,
  primeiroErro,
  hoje,
  onFiltrar,
}: {
  padroes: ErrosPainel['padroes']
  porCategoria: ErrosPainel['por_categoria']
  dias: number
  desde: string
  primeiroErro: string | null
  hoje: string
  onFiltrar: (categoria: string) => void
}) {
  // o filtro da API é por prefixo: o padrão "particula" conta todas as partículas
  const errosDe = (p: Padrao) => porCategoria.filter((c) => c.categoria.startsWith(p.categoria)).reduce((s, c) => s + c.n, 0)
  // O registro erro a erro começou em 16/10: "nenhum erro em 90 dias" sobre um período em
  // que nada era registrado diria mais do que os dados sabem.
  const semErro = () =>
    !primeiroErro
      ? 'nenhum erro registrado ainda'
      : primeiroErro > desde
        ? `nenhum erro desde ${ddmm(primeiroErro)}, quando o registro começou`
        : `nenhum erro registrado em ${dias} dias`

  return (
    <Secao titulo="Padrões em vigília" icone={<Eye />}>
      <Tabs defaultValue="abertos" className="gap-3">
        <TabsList>
          <TabsTrigger value="abertos">Abertos ({padroes.abertos.length})</TabsTrigger>
          <TabsTrigger value="resolvidos">Resolvidos ({padroes.resolvidos.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="abertos">
          {padroes.abertos.length === 0 ? (
            <Vazio>Nenhum padrão aberto.</Vazio>
          ) : (
            <ul className="divide-y">
              {padroes.abertos.map((p) => {
                const n = errosDe(p)
                return (
                  <li key={p.id} className="space-y-1.5 py-3 first:pt-0 last:pb-0">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <BotaoCategoria categoria={p.categoria} onFiltrar={onFiltrar} />
                      <span className="text-xs text-muted-foreground">
                        aberto há {plural(diasEntre(p.aberto_em, hoje), 'dia', 'dias')} ({ddmm(p.aberto_em)}) ·{' '}
                        {n ? `${plural(n, 'erro', 'erros')} em ${dias} dias` : semErro()}
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed">
                      <TextoMisto texto={p.descricao} classeJa="text-[15px]" />
                    </p>
                  </li>
                )
              })}
            </ul>
          )}
        </TabsContent>

        <TabsContent value="resolvidos">
          {padroes.resolvidos.length === 0 ? (
            <Vazio>
              Nenhum padrão resolvido ainda. Quando o tutor fecha um padrão, com a evidência de que o erro parou de aparecer, ele vem para cá com a nota
              do que funcionou.
            </Vazio>
          ) : (
            <ul className="divide-y">
              {padroes.resolvidos.map((p) => (
                <li key={p.id} className="space-y-1.5 py-3 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <BotaoCategoria categoria={p.categoria} onFiltrar={onFiltrar} />
                    <span className="flex items-center gap-1 text-xs text-ok">
                      <CircleCheck className="size-3.5" />
                      resolvido {p.resolvido_em ? `em ${ddmm(p.resolvido_em)}` : ''}
                    </span>
                    {p.resolvido_em && (
                      <span className="text-xs text-muted-foreground">
                        depois de {plural(diasEntre(p.aberto_em, p.resolvido_em), 'dia', 'dias')} aberto
                      </span>
                    )}
                  </div>
                  {p.nota && (
                    <p className="text-sm leading-relaxed">
                      <TextoMisto texto={p.nota} classeJa="text-[15px]" />
                    </p>
                  )}
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    <TextoMisto texto={p.descricao} />
                  </p>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>
    </Secao>
  )
}
