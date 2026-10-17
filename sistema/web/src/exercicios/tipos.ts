import type { Bloco, Exercicio, Resultado, RespostaDe, PorTipo, TipoExercicio } from '@/api/types'

export const ROTULO_TIPO: Record<TipoExercicio, string> = {
  escolha: 'Escolha',
  achar_erro: 'Ache o erro',
  ligar: 'Ligue os pares',
  ordenar: 'Ordene',
  completar: 'Complete',
  digitar: 'Digite',
  conjugar: 'Conjugue',
  producao: 'Produção',
}

export const ROTULO_BLOCO: Record<Bloco, string> = {
  aquecimento: 'Aquecimento',
  verificacao: 'Verificação',
  producao: 'Produção',
  revisao: 'Revisão',
}

/** O contrato comum dos widgets: mostram o render, devolvem a resposta (null = incompleta). */
export interface PropsWidget<T extends TipoExercicio> {
  render: PorTipo[T]['render']
  /** preenchido = já respondido: o widget fica só leitura e mostra o detalhe da correção */
  resultado: Resultado<T> | null
  onChange: (resposta: RespostaDe<T> | null) => void
}

/** A resposta dele em uma linha, para o resumo do fim da lição. */
export function respostaEmTexto(ex: Exercicio, r: Resultado): string {
  // o resultado é do mesmo exercício: o tipo da resposta acompanha ex.tipo
  const de = <T extends TipoExercicio>() => r.resposta as RespostaDe<T>
  switch (ex.tipo) {
    case 'escolha':
      return de<'escolha'>().opcao ?? ''
    case 'digitar':
    case 'conjugar':
      return de<'digitar'>().texto ?? ''
    case 'ordenar':
      return (de<'ordenar'>().pecas ?? []).join('')
    case 'completar':
      return (de<'completar'>().lacunas ?? []).join(' / ')
    case 'ligar':
      return (de<'ligar'>().pares ?? []).map(([a, b]) => `${a} — ${b}`).join(' · ')
    case 'achar_erro':
      return ex.render.segmentos[de<'achar_erro'>().segmento] ?? ''
    case 'producao':
      return (de<'producao'>().frases ?? []).join(' / ')
  }
}
