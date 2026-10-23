import type { Bloco, Exercicio, Resultado, RespostaDe, PorTipo, TipoExercicio } from '@/api/types'

export const ROTULO_TIPO: Record<TipoExercicio, string> = {
  escolha: 'Escolha',
  achar_erro: 'Ache o erro',
  ligar: 'Ligue os pares',
  ordenar: 'Ordene',
  completar: 'Complete',
  digitar: 'Digite',
  conjugar: 'Conjugue',
  ouvir: 'Ouça',
  producao: 'Produção',
  explicacao: 'Explicação',
}

export const ROTULO_BLOCO: Record<Bloco, string> = {
  aquecimento: 'Aquecimento',
  novo: 'Conteúdo novo',
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
    case 'ouvir': {
      const r = de<'ouvir'>()
      return 'texto' in r ? r.texto : r.opcao
    }
    case 'producao':
      return (de<'producao'>().frases ?? []).join(' / ')
    case 'explicacao':
      return ''
  }
}

/** A explicação não é exercício: fica fora do placar, da barra de progresso e do "concluída" (§9.2). */
export const ehExercicio = (ex: Exercicio) => ex.tipo !== 'explicacao'

/** id → número do exercício na lição (1, 2, 3…), pulando as explicações: o mesmo número na barra e no resumo. */
export function numerarExercicios(l: { exercicios: Exercicio[] }): Map<number, number> {
  return new Map(l.exercicios.filter(ehExercicio).map((e, i) => [e.id, i + 1]))
}

/** A 1ª resposta saiu errada num exercício com dica e a 2ª tentativa ainda não veio (§9.6). */
export const aguardandoDica = (r: Resultado | null | undefined): boolean => !!r?.dica && !r.segunda

/**
 * O que o widget mostra depois da dica: a 2ª tentativa, se houve (a resposta e a correção dela);
 * na desistência, a 1ª, já com o detalhe da correção. O placar continua sendo o da 1ª.
 */
export function paraWidget(r: Resultado): Resultado {
  const s = r.segunda
  return s && 'resposta' in s ? { ...r, veredito: s.veredito, resposta: s.resposta, detalhe: s.detalhe } : r
}
