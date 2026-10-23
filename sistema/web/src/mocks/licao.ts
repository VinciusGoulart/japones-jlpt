// Lição fictícia com os 9 tipos, para desenvolver e testar respostas sem tocar
// no banco real. Conteúdo genérico de livro-texto N5: nada de dado pessoal aqui
// (o repositório é público).
import { ErroApi } from '@/api/client'
import { normalizar } from '@/lib/texto'
import type {
  Correcao,
  Exercicio,
  Licao,
  OpDiff,
  Resultado,
  TipoExercicio,
  Veredito,
} from '@/api/types'

/** O `dados` do servidor (com gabarito), por exercício. */
type Dados = Record<string, unknown>

interface ExMock {
  ex: Omit<Exercicio, 'resultado'>
  dados: Dados
  explicacao: string
  /** a dica da 2ª tentativa (§9.6), quando a 1ª sai errada */
  dica?: string
}

// o texto da explicação reaproveita as regras que os exercícios abaixo já explicam
const MD_EXPLICACAO = [
  '**に × で** — o verbo decide a partícula do lugar:',
  '',
  '| Partícula | Uso |',
  '|---|---|',
  '| に | onde algo está ou para onde se vai |',
  '| で | onde a AÇÃO acontece |',
  '',
  '- ある para coisas e plantas; いる para pessoas e animais.',
].join('\n')

const exercicios: ExMock[] = [
  {
    // não é exercício: o painel mostra o texto e o botão Entendi (§9.2)
    ex: {
      id: 100, ordem: 0, bloco: 'novo', tipo: 'explicacao', categoria: null,
      enunciado: 'Conteúdo novo: に × で',
      render: { md: MD_EXPLICACAO, titulo: null, regra: null },
    },
    dados: { md: MD_EXPLICACAO },
    explicacao: '',
  },
  {
    ex: {
      id: 101, ordem: 1, bloco: 'aquecimento', tipo: 'escolha', categoria: 'particula:ni-de',
      enunciado: 'Qual partícula completa a frase? 図書館＿本を読みます。',
      render: { opcoes: ['に', 'で', 'を', 'が'] },
    },
    dados: { opcoes: ['で', 'に', 'を', 'が'], correta: 'で' },
    explicacao: 'Lugar onde a AÇÃO acontece leva で. に marca onde algo está ou para onde se vai.',
    dica: 'Confira o verbo: 読みます é uma ação ou um estar/ir?',
  },
  {
    ex: {
      id: 102, ordem: 2, bloco: 'verificacao', tipo: 'ligar', categoria: 'forma-te',
      enunciado: 'Ligue cada verbo à forma て.',
      render: { esquerda: ['飲む', '書く', '待つ', '食べる'], direita: ['待って', '食べて', '書いて', '飲んで'] },
    },
    dados: { pares: [['書く', '書いて'], ['飲む', '飲んで'], ['待つ', '待って'], ['食べる', '食べて']] },
    explicacao: 'む/ぶ/ぬ → んで · く → いて · う/つ/る → って · ichidan: tira る e põe て.',
  },
  {
    ex: {
      id: 103, ordem: 3, bloco: 'verificacao', tipo: 'achar_erro', categoria: 'particula:wo',
      enunciado: 'Uma parte desta frase está errada. Qual?',
      render: { segmentos: ['毎朝、', '駅を', '行きます。'] },
    },
    dados: { segmentos: ['毎朝、', '駅を', '行きます。'], errado: 1, correcao: '駅に' },
    explicacao: 'Destino de 行く leva に (ou へ). を com verbo de movimento é o lugar por onde se passa.',
  },
  {
    ex: {
      id: 104, ordem: 4, bloco: 'verificacao', tipo: 'ordenar', categoria: 'ordem',
      enunciado: 'Monte a frase: "Há um gato embaixo da mesa."',
      render: { pecas: ['います', '下に', '猫が', 'で', 'テーブルの'] },
    },
    dados: { pecas: ['テーブルの', '下に', '猫が', 'います'], aceitas: [['テーブルの', '下に', '猫が', 'います']], distratores: ['で'] },
    explicacao: 'Lugar に + coisa が + います/あります: o lugar costuma vir primeiro.',
  },
  {
    ex: {
      id: 105, ordem: 5, bloco: 'verificacao', tipo: 'completar', categoria: 'particula:wa-ga',
      enunciado: 'Complete as lacunas.',
      render: {
        partes: ['わたし', { lacuna: 0, opcoes: ['が', 'は', 'を', 'に'] }, '毎日', { lacuna: 1 }, 'コーヒーを飲みます。'],
      },
    },
    dados: {
      texto: 'わたし{0}毎日{1}コーヒーを飲みます。',
      lacunas: [{ aceitas: ['は'], opcoes: ['は', 'が', 'を', 'に'] }, { aceitas: ['あさ', '朝'] }],
    },
    explicacao: 'は marca o tópico (de quem se fala). 朝（あさ）= manhã; sem partícula antes do verbo aqui.',
  },
  {
    ex: {
      id: 106, ordem: 6, bloco: 'verificacao', tipo: 'conjugar', categoria: 'forma-ta',
      enunciado: 'Escreva a forma た.',
      render: { verbo: '行く', leitura: 'いく', forma: 'forma た (passado casual)' },
    },
    dados: { verbo: '行く', leitura: 'いく', forma: 'forma た (passado casual)', aceitas: ['行った', 'いった'] },
    explicacao: '行く é a exceção do grupo く: vira 行って / 行った, não 行いた.',
  },
  {
    ex: {
      id: 107, ordem: 7, bloco: 'revisao', tipo: 'digitar', categoria: 'vocabulario',
      enunciado: 'Escreva em japonês: "Eu nunca fui ao Japão."',
      render: { dica: 'use 〜たことがありません' },
    },
    dados: { aceitas: ['日本に行ったことがありません', 'にほんにいったことがありません'], dica: 'use 〜たことがありません' },
    explicacao: 'Experiência: verbo na forma た + ことがあります; negativa: ことがありません.',
  },
  {
    ex: {
      id: 108, ordem: 8, bloco: 'verificacao', tipo: 'escolha', categoria: 'iru-aru',
      enunciado: 'Escolha a frase certa para "Tem um livro na bolsa."',
      render: { opcoes: ['かばんの中に本がいます。', 'かばんの中に本があります。', 'かばんの中で本があります。'] },
    },
    dados: { opcoes: ['かばんの中に本があります。', 'かばんの中に本がいます。', 'かばんの中で本があります。'], correta: 'かばんの中に本があります。' },
    explicacao: 'ある para coisas e plantas; いる para pessoas e animais.',
  },
  {
    // sem áudio de propósito: o mock não tem mp3, e assim o caminho "não foi gravado" fica testável
    ex: {
      id: 110, ordem: 9, bloco: 'revisao', tipo: 'ouvir', categoria: 'forma-ta',
      enunciado: 'Ouça e escreva a frase em japonês.',
      render: { modo: 'ditado', audio: null },
    },
    dados: { texto: '日本に行ったことがあります', aceitas: ['日本に行ったことがあります', 'にほんにいったことがあります'] },
    explicacao: 'Experiência: verbo na forma た + ことがあります.',
  },
  {
    ex: {
      id: 109, ordem: 10, bloco: 'producao', tipo: 'producao', categoria: null,
      enunciado: 'Escreva três frases sobre lugares onde você já foi ou nunca foi.',
      render: { minimo: 3, dicas: ['〜に行ったことがあります', '〜に行ったことがありません', 'もう / まだ'] },
    },
    dados: { minimo: 3, dicas: [] },
    explicacao: 'Experiência = forma た + ことがあります.',
  },
]

const respostas = new Map<number, Resultado>()

export function licaoMock(): Licao {
  return {
    id: 1,
    data: '2026-10-17',
    titulo: 'Lição de exemplo — partículas e experiência',
    status: exercicios.every((e) => e.ex.tipo === 'explicacao' || respostas.has(e.ex.id)) ? 'concluida' : 'aberta',
    exercicios: exercicios.map((e) => ({ ...e.ex, resultado: respostas.get(e.ex.id) ?? null }) as Exercicio),
  }
}

// ------------------------------------------------------------------ correção (espelha exercicios.py)

function diff(resposta: string, alvo: string): OpDiff[] {
  const a = [...normalizar(resposta)]
  const b = [...normalizar(alvo)]
  const lcs = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0))
  for (let i = a.length - 1; i >= 0; i--)
    for (let j = b.length - 1; j >= 0; j--)
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1])
  const ops: OpDiff[] = []
  const push = (op: OpDiff['op'], t: string) => {
    const ult = ops[ops.length - 1]
    if (ult && ult.op === op) ult.texto += t
    else ops.push({ op, texto: t })
  }
  let i = 0
  let j = 0
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) { push('igual', a[i]); i++; j++ }
    else if (j < b.length && (i >= a.length || lcs[i][j + 1] >= lcs[i + 1][j])) { push('faltou', b[j]); j++ }
    else { push('sobrou', a[i]); i++ }
  }
  return ops
}

function maisParecida(t: string, aceitas: string[]): string {
  const n = normalizar(t)
  const parecida = (x: string) => {
    const m = normalizar(x)
    let comum = 0
    for (const c of n) if (m.includes(c)) comum++
    return comum / Math.max(m.length, n.length, 1)
  }
  return aceitas.reduce((melhor, x) => (parecida(x) > parecida(melhor) ? x : melhor), aceitas[0])
}

type Resp = Record<string, unknown>

function corrigir(tipo: TipoExercicio, d: Dados, r: Resp): [Veredito, string, Record<string, unknown>] {
  const ok = (b: boolean): Veredito => (b ? 'certo' : 'errado')
  switch (tipo) {
    case 'escolha':
      return [ok(normalizar(String(r.opcao ?? '')) === normalizar(String(d.correta))), String(d.correta), {}]
    case 'achar_erro': {
      const segs = d.segmentos as string[]
      const i = d.errado as number
      return [ok(r.segmento === i), `${segs[i]} → ${String(d.correcao)}`, { errado: i, correcao: d.correcao }]
    }
    case 'ligar': {
      const pares = d.pares as [string, string][]
      const esc = new Map((r.pares as [string, string][]) ?? [])
      const det = pares.map(([a, b]) => ({ esquerda: a, escolhida: esc.get(a) ?? null, certa: b, ok: esc.get(a) === b }))
      return [ok(det.every((x) => x.ok)), pares.map(([a, b]) => `${a} — ${b}`).join(' · '), { pares: det }]
    }
    case 'ordenar': {
      const montada = ((r.pecas as string[]) ?? []).join('')
      const aceitas = ((d.aceitas as string[][]) ?? [d.pecas as string[]]).map((a) => a.join(''))
      return [ok(aceitas.some((a) => normalizar(a) === normalizar(montada))), aceitas[0], { montada }]
    }
    case 'completar': {
      const lac = d.lacunas as { aceitas: string[] }[]
      const dadas = (r.lacunas as string[]) ?? []
      const oks = lac.map((l, i) => i < dadas.length && l.aceitas.some((a) => normalizar(a) === normalizar(dadas[i])))
      const gab = String(d.texto).replace(/\{(\d+)\}/g, (_, n: string) => lac[Number(n)].aceitas[0])
      return [ok(oks.every(Boolean)), gab, { lacunas: oks }]
    }
    case 'digitar':
    case 'conjugar': {
      const t = String(r.texto ?? '')
      const aceitas = d.aceitas as string[]
      const alvo = maisParecida(t, aceitas)
      const det = { diff: diff(t, alvo), comparado_com: alvo }
      if (aceitas.some((a) => normalizar(a) === normalizar(t))) return ['certo', aceitas[0], det]
      return [tipo === 'digitar' ? 'revisar' : 'errado', aceitas[0], det]
    }
    case 'ouvir': {
      if (d.opcoes) return [ok(normalizar(String(r.opcao ?? '')) === normalizar(String(d.correta))), `${d.texto} → ${d.correta}`, {}]
      const t = String(r.texto ?? '')
      const aceitas = (d.aceitas as string[] | undefined) ?? [String(d.texto)]
      const alvo = maisParecida(t, aceitas)
      const det = { diff: diff(t, alvo), comparado_com: alvo }
      return [aceitas.some((a) => normalizar(a) === normalizar(t)) ? 'certo' : 'revisar', aceitas[0], det]
    }
    case 'producao':
      return ['revisar', '', {}]
    case 'explicacao':      // a API real devolve 400
      throw new Error('explicação não tem resposta')
  }
}

export function responderExercicioMock(exercicioId: number, corpo: { resposta: Resp }): Correcao {
  const e = exercicios.find((x) => x.ex.id === exercicioId)
  if (!e) throw new Error('exercício não encontrado')
  const [veredito, gabarito, detalhe] = corrigir(e.ex.tipo, e.dados, corpo.resposta)
  const anterior = respostas.get(exercicioId)
  // a 2ª tentativa depois da dica (§9.6): o placar fica com a 1ª
  if (anterior?.dica && !anterior.segunda) {
    const autocorrigiu = veredito === 'certo'
    respostas.set(exercicioId, {
      ...anterior, gabarito, explicacao: e.explicacao, autocorrigiu,
      segunda: { resposta: corpo.resposta, veredito, detalhe },
    } as unknown as Resultado)
    return { veredito, gabarito, explicacao: e.explicacao, detalhe, contou: false, autocorrigiu } as Correcao
  }
  if (!anterior && veredito === 'errado' && e.dica) {
    respostas.set(exercicioId, {
      veredito, resposta: corpo.resposta, gabarito: '', explicacao: null, detalhe: {}, correcao: null,
      dica: e.dica, segunda: null, autocorrigiu: null, primeiro: { gabarito, detalhe },
    } as unknown as Resultado)
    return { veredito, gabarito: '', explicacao: null, detalhe: {}, contou: true, dica: e.dica } as Correcao
  }
  const contou = !respostas.has(exercicioId)
  if (contou) {
    respostas.set(exercicioId, {
      veredito, gabarito, explicacao: e.explicacao, detalhe, correcao: null,
      resposta: corpo.resposta,
    } as unknown as Resultado)
    // O "tutor" do mock corrige a produção 25 s depois, para exercitar o polling.
    if (veredito === 'revisar') {
      setTimeout(() => {
        const atual = respostas.get(exercicioId)
        if (atual)
          respostas.set(exercicioId, {
            ...atual,
            veredito: 'certo',
            correcao: '**Boa!** As frases estão certas.\n\n- 「日本に行ったことがあります」✓\n- Atenção ao に de destino.',
          })
      }, 25_000)
    }
  }
  return { veredito, gabarito, explicacao: e.explicacao, detalhe, contou } as Correcao
}

/** "Ver a resposta" com a dica pendente: lacuna, e a correção da 1ª aparece (§9.6). */
export function desistirMock(exercicioId: number): Correcao {
  const e = exercicios.find((x) => x.ex.id === exercicioId)
  const anterior = respostas.get(exercicioId) as (Resultado & { primeiro?: { gabarito: string; detalhe: object } }) | undefined
  if (!e || !anterior?.dica || anterior.segunda) throw new ErroApi(409, 'este exercício não tem dica esperando a 2ª tentativa')
  const { gabarito, detalhe } = anterior.primeiro ?? { gabarito: '', detalhe: {} }
  respostas.set(exercicioId, { ...anterior, gabarito, detalhe, explicacao: e.explicacao, segunda: { desistiu: true }, autocorrigiu: false } as Resultado)
  return { veredito: 'errado', gabarito, explicacao: e.explicacao, detalhe, contou: false, autocorrigiu: false } as Correcao
}
