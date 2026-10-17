import { useEffect, useState } from 'react'

/** O valor só muda depois de `ms` sem mudanças (busca enquanto digita). */
export function useAtrasado<T>(valor: T, ms = 300): T {
  const [v, setV] = useState(valor)
  useEffect(() => {
    const t = setTimeout(() => setV(valor), ms)
    return () => clearTimeout(t)
  }, [valor, ms])
  return v
}
