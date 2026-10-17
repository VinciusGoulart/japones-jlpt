import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'

const componentes: Components = {
  // links externos (Trello, jlpt.jp) abrem em outra aba; os internos seguem no painel
  a: ({ href, children, node: _node, ...props }) => {
    const externo = !!href && /^https?:/.test(href)
    return (
      <a href={href} {...props} {...(externo ? { target: '_blank', rel: 'noreferrer' } : {})}>
        {children}
      </a>
    )
  },
}

/** Markdown com tabelas (GFM). `inline` para textos de uma linha, como o plano do dia. */
export function Markdown({ texto, className, inline }: { texto: string; className?: string; inline?: boolean }) {
  return (
    <div className={cn('md', inline && 'md-inline', className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={componentes}>
        {texto}
      </ReactMarkdown>
    </div>
  )
}
