// Cliente fino da API (DESIGN §10). Com VITE_MOCK=1 as chamadas vão para os
// fixtures de src/mocks — para desenvolver sem o backend e testar respostas sem
// sujar o placar real (só a primeira resposta conta, e ela grava erro no banco).
import type {
  AnkiPainel,
  BuscaKotoba,
  Erros,
  ErrosPainel,
  HistoricoKotoba,
  KanjiKotoba,
  ListasKotoba,
  RegistroAntigo,
  AulaCompleta,
  AulaResumo,
  Calendario,
  Correcao,
  CorpoResposta,
  Hoje,
  Licao,
  LicaoResumo,
  Regra,
} from './types'

export class ErroApi extends Error {
  readonly status: number
  constructor(status: number, mensagem: string) {
    super(mensagem)
    this.name = 'ErroApi'
    this.status = status
  }
}

export const MOCK = import.meta.env.VITE_MOCK === '1'

async function pedir<T>(caminho: string, init?: RequestInit): Promise<T> {
  if (MOCK) {
    const { responderMock } = await import('@/mocks')
    return responderMock<T>(caminho, init)
  }
  let r: Response
  try {
    r = await fetch(caminho, {
      ...init,
      headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}) },
    })
  } catch {
    throw new ErroApi(0, 'API fora do ar (127.0.0.1:8787). O serviço japones-painel está rodando?')
  }
  if (!r.ok) {
    let detalhe = r.statusText
    try {
      const corpo: unknown = await r.json()
      if (corpo && typeof corpo === 'object' && 'detail' in corpo) detalhe = String(corpo.detail)
    } catch {
      /* corpo não era JSON */
    }
    throw new ErroApi(r.status, detalhe || `HTTP ${r.status}`)
  }
  return (await r.json()) as T
}

const qs = (p: Record<string, string | number | undefined>) => {
  const s = new URLSearchParams()
  for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== '') s.set(k, String(v))
  const t = s.toString()
  return t ? `?${t}` : ''
}

export const api = {
  hoje: () => pedir<Hoje>('/api/hoje'),
  aulas: (ultimas: number, busca?: string) => pedir<AulaResumo[]>(`/api/aulas${qs({ ultimas, busca })}`),
  aula: (data: string) => pedir<AulaCompleta[]>(`/api/aulas/${encodeURIComponent(data)}`),
  calendario: (de: string, ate: string) => pedir<Calendario>(`/api/calendario${qs({ de, ate })}`),
  licoes: (ultimas = 20) => pedir<LicaoResumo[]>(`/api/licoes${qs({ ultimas })}`),
  /** null quando ainda não existe lição (a API responde 404) */
  licaoAtual: async (): Promise<Licao | null> => {
    try {
      return await pedir<Licao>('/api/licoes/atual')
    } catch (e) {
      if (e instanceof ErroApi && e.status === 404) return null
      throw e
    }
  },
  licao: (id: number) => pedir<Licao>(`/api/licoes/${id}`),
  responder: (exercicioId: number, corpo: CorpoResposta) =>
    pedir<Correcao>(`/api/exercicios/${exercicioId}/resposta`, { method: 'POST', body: JSON.stringify(corpo) }),
  /** o caderno de regras (§13.6) */
  regras: () => pedir<Regra[]>('/api/regras'),

  // Fase 3 (DESIGN §12)
  erros: (dias: number, categoria?: string) => pedir<Erros>(`/api/erros${qs({ dias, categoria })}`),
  errosPainel: (dias: number) => pedir<ErrosPainel>(`/api/erros/painel${qs({ dias })}`),
  registro: (busca: string, limite = 20) => pedir<RegistroAntigo[]>(`/api/registro${qs({ busca, limite })}`),
  ankiPainel: () => pedir<AnkiPainel>('/api/anki/painel'),
  kotobaBuscar: (q: string, limite = 20) => pedir<BuscaKotoba>(`/api/kotoba/buscar${qs({ q, limite })}`),
  /** null quando o kanji não está no dicionário (a API responde 404) */
  kotobaKanji: async (literal: string): Promise<KanjiKotoba | null> => {
    try {
      return await pedir<KanjiKotoba>(`/api/kotoba/kanji/${encodeURIComponent(literal)}`)
    } catch (e) {
      if (e instanceof ErroApi && e.status === 404) return null
      throw e
    }
  },
  kotobaHistorico: (dias: number) => pedir<HistoricoKotoba>(`/api/kotoba/historico${qs({ dias })}`),
  kotobaListas: () => pedir<ListasKotoba>('/api/kotoba/listas'),
}
