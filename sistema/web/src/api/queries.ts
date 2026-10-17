import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { Licao } from './types'

export const chaves = {
  hoje: ['hoje'] as const,
  aulas: (busca: string) => ['aulas', busca] as const,
  aula: (data: string) => ['aula', data] as const,
  calendario: (de: string, ate: string) => ['calendario', de, ate] as const,
  licoes: ['licoes'] as const,
  licaoAtual: ['licao', 'atual'] as const,
  licao: (id: number) => ['licao', id] as const,
}

// hoje() lê o Trello e copia a coleção do Anki (~3 s): relê ao voltar para a janela, não em intervalo
export const useHoje = () => useQuery({ queryKey: chaves.hoje, queryFn: api.hoje, staleTime: 60_000 })

export const useAulas = (busca: string) =>
  useQuery({ queryKey: chaves.aulas(busca), queryFn: () => api.aulas(200, busca), placeholderData: keepPreviousData })

export const useAula = (data: string) => useQuery({ queryKey: chaves.aula(data), queryFn: () => api.aula(data) })

export const useCalendario = (de: string | null, ate: string | null) =>
  useQuery({
    queryKey: chaves.calendario(de ?? '', ate ?? ''),
    queryFn: () => api.calendario(de!, ate!),
    enabled: !!de && !!ate,
    placeholderData: keepPreviousData,
  })

export const useLicoes = () => useQuery({ queryKey: chaves.licoes, queryFn: () => api.licoes(20) })

// Enquanto houver produção (ou digitar fora da lista) esperando o tutor, a lição
// é relida a cada 20 s e ao voltar para a janela: a correção é feita pelo MCP, no
// terminal, e tem de aparecer aqui sem ele recarregar a página.
const esperandoTutor = (q: { state: { data?: Licao | null } }) =>
  q.state.data?.exercicios.some((e) => e.resultado?.veredito === 'revisar') ? 20_000 : false

export const useLicaoAtual = () =>
  useQuery({ queryKey: chaves.licaoAtual, queryFn: api.licaoAtual, refetchInterval: esperandoTutor, refetchOnWindowFocus: true })

export const useLicao = (id: number) =>
  useQuery({
    queryKey: chaves.licao(id),
    queryFn: () => api.licao(id),
    refetchInterval: esperandoTutor,
    refetchOnWindowFocus: true,
  })
