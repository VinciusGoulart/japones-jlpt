import { useLayoutEffect, useRef, useState } from 'react'

/**
 * A largura atual de um elemento. O mapa de calor precisa dela para decidir o
 * tamanho da célula: poucas semanas cabem com célula grande; com um ano de plano
 * a célula encolhe até o mínimo legível e, daí para baixo, o mapa rola por dentro.
 */
export function useLargura<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [largura, setLargura] = useState(0)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    setLargura(el.clientWidth)
    const obs = new ResizeObserver(([e]) => setLargura(Math.floor(e.contentRect.width)))
    obs.observe(el)
    return () => obs.disconnect()
  }, [])
  return [ref, largura] as const
}
