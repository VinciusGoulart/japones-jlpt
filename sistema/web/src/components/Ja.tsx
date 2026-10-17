import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'
import { trechos } from '@/lib/texto'

/** Texto só em japonês: lang="ja" escolhe os glifos japoneses e as regras de quebra de linha. */
export function Ja({ className, ...props }: ComponentProps<'span'>) {
  return <span lang="ja" className={cn('font-ja', className)} {...props} />
}

/**
 * Texto misto (português com japonês no meio, como os enunciados): cada trecho
 * japonês ganha lang="ja" e, se pedido, um tamanho maior — a leitura do japonês
 * importa mais que a densidade.
 */
export function TextoMisto({ texto, classeJa }: { texto: string; classeJa?: string }) {
  return (
    <>
      {trechos(texto).map((t, i) =>
        t.ja ? (
          <Ja key={i} className={classeJa}>
            {t.texto}
          </Ja>
        ) : (
          <span key={i}>{t.texto}</span>
        ),
      )}
    </>
  )
}
