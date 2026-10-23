// Roteador dos fixtures (VITE_MOCK=1). Dados fictícios: o repositório é público.
import type { AulaCompleta, AulaResumo, Calendario, DiaCalendario, Hoje, LicaoResumo, Regra } from '@/api/types'
import { ErroApi } from '@/api/client'
import { diaDeEstudoLocal, paraData, paraIso, somarDias } from '@/lib/datas'
import { licaoMock, responderExercicioMock } from './licao'

const hojeIso = paraIso(diaDeEstudoLocal())
const dia = (n: number) => paraIso(somarDias(paraData(hojeIso), n))

const hoje: Hoje = {
  agora: `${hojeIso} 21:10 (Sat)`,
  dia_de_estudo: hojeIso,
  dia_do_plano: 42,
  streak: { atual_ate_ontem: 5, recorde: 12 },
  ultima_aula: {
    data: dia(-1), dia: 41, tipo: 'completa', titulo: 'Forma た',
    deixou_para_hoje: 'retomar **に × で** com frases de lugar + 5 verbos na forma た.', dias_atras: 1,
  },
  plano_de_hoje: '**に × で pelo verbo**: estar/ir → に, fazer → で · *revisão da forma た*',
  proximos: [`${dia(1)} (dom): **Kanji da semana** + planejamento`],
  lembrete_abertura: { texto: 'Abrir com 3 frases de aquecimento sem explicação.', de: `${dia(-1)} 22:40:00` },
  padroes_abertos: [
    { id: 1, categoria: 'particula:wo', descricao: 'を antes de verbo de movimento: 駅を行きます.', aberto_em: dia(-6) },
    { id: 2, categoria: 'iru-aru', descricao: 'いる × ある trocados para objetos.', aberto_em: dia(-10) },
  ],
  avisos: ['DOMINGO: planejar a semana seguinte.'],
  trello: {
    pendencias_7_dias: [
      { nome: 'Fazer as questões de exemplo do N5', vence: dia(-1), vencido: true, url: 'https://trello.com/' },
      { nome: 'Importar o deck novo', vence: hojeIso, vencido: false, url: 'https://trello.com/' },
      { nome: 'Reavaliar novos/dia no Anki', vence: dia(3), vencido: false, url: 'https://trello.com/' },
    ],
    semana_atual: [
      { card: 'Semana 6 — partículas de lugar', checklists: [{ nome: 'Mesa (1h)', feitos: '4/7', faltam: ['Sáb', 'Dom', 'Qua'] }] },
      { card: 'Semana 6 — áudio', checklists: [{ nome: '30 minutos', feitos: '7/7', faltam: [] }] },
    ],
    avisos_jlpt: [{ nome: 'Exemplo de aviso do JLPT', url: 'https://trello.com/' }],
  },
  anki: {
    leitura: 'desktop, há 0.1 dia(s)',
    hoje: { cartoes: 35, minutos: 9 },
    ontem: { cartoes: 180, minutos: 41 },
    fila_atrasados: 120,
    alerta_fila: 'não subir novos',
    retencao_30d: 83.2,
    alerta_retencao: 'abaixo de 85%: reduzir novos',
    em_loop: ['情報 (9x)', '失う (7x)', '特に (6x)'],
    bandeira: ['frase marcada para rever'],
  },
}

const aulas: AulaCompleta[] = Array.from({ length: 12 }, (_, i) => {
  const data = dia(-1 - i)
  const tipo = i % 5 === 3 ? 'sem_mesa' : i % 4 === 2 ? 'parcial' : 'completa'
  const titulo = tipo === 'sem_mesa' ? null : ['Forma た', 'に × で', 'Adjetivos い', 'Contadores'][i % 4]
  return {
    id: 100 - i, data, dia_plano: 41 - i, tipo, titulo, fase: 1, semana: 6,
    inicio: tipo === 'sem_mesa' ? null : '21:30', minutos: tipo === 'sem_mesa' ? null : 60,
    verif_ok: tipo === 'sem_mesa' ? null : 3, verif_total: tipo === 'sem_mesa' ? null : 5,
    prod_ok: tipo === 'completa' ? 2 : null, prod_total: tipo === 'completa' ? 4 : null,
    origem: 'mcp', criado_em: `${data} 22:30:00`,
    texto_md: `## ${data} (dia ${41 - i} do plano) — ${titulo ?? 'sem mesa'}\n\n**Conteúdo:** exemplo de entrada do diário.\n\n| Bloco | Placar |\n|---|---|\n| Verificação | 3/5 |\n| Produção | 2/4 |\n\n- 猫（ねこ）が部屋（へや）にいます — "o gato está no quarto"\n- **Amanhã:** revisão.`,
  } satisfies AulaCompleta
})

function calendario(de: string, ate: string): Calendario {
  const dias: DiaCalendario[] = []
  for (let d = paraData(de); paraIso(d) <= ate; d = somarDias(d, 1)) {
    const iso = paraIso(d)
    const a = aulas.find((x) => x.data === iso)
    dias.push({
      data: iso,
      aulas: a ? [{ tipo: a.tipo, titulo: a.titulo, dia_plano: a.dia_plano, verif_ok: a.verif_ok, verif_total: a.verif_total, prod_ok: a.prod_ok, prod_total: a.prod_total }] : [],
      trajeto: iso <= hojeIso && iso >= dia(-14) ? { anki_cartoes: 150, anki_minutos: 35.5, audio: d.getDate() % 3 ? 1 : 0 } : null,
      plano: iso >= dia(-3) && iso <= dia(4) ? '**Plano** do dia: revisão + conteúdo novo' : null,
      licoes: iso === hojeIso ? [{ id: 1, titulo: 'Lição de exemplo', status: 'aberta' }] : [],
    })
  }
  return {
    dias,
    eventos_trello: [
      { nome: 'Importar o deck novo', vence: hojeIso, url: 'https://trello.com/', concluido: false, lista: 'Pendências' },
      { nome: 'Questões de exemplo', vence: dia(-1), url: 'https://trello.com/', concluido: true, lista: 'Pendências' },
    ].filter((e) => e.vence >= de && e.vence <= ate),
  }
}

// o caderno de regras (§13.6): uma por grupo, com o texto das regras que a lição fictícia já usa
const regra = (r: Partial<Regra> & Pick<Regra, 'slug' | 'titulo' | 'status' | 'dias'>): Regra => ({
  categoria: null, ensinada_em: dia(-20), explicacao_md: null, intervalo: 2, proxima: r.dias === null ? null : dia(r.dias),
  acertos: 1, erros: 0, ultima_revisao: dia(-2), ultima_falha: null, ...r,
})
const regras: Regra[] = [
  regra({ slug: 'ni-de', titulo: 'に × で pelo verbo', categoria: 'particula:ni-de', status: 'vencida', dias: -1,
          explicacao_md: '| Partícula | Uso |\n|---|---|\n| に | onde algo está ou para onde se vai |\n| で | onde a AÇÃO acontece |' }),
  regra({ slug: 'iru-aru', titulo: 'いる × ある', categoria: 'iru-aru', status: 'fragil', dias: 1, intervalo: 1, acertos: 1, erros: 3,
          ultima_falha: dia(0), explicacao_md: '- ある para coisas e plantas\n- いる para pessoas e animais' }),
  regra({ slug: 'forma-ta', titulo: 'Forma た', categoria: 'forma-ta', status: 'em_dia', dias: 12, intervalo: 12, acertos: 4,
          explicacao_md: '行く é a exceção do grupo く: vira **行って / 行った**.' }),
]

const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms))

// os corpos enviados ficam visíveis no console (window.__corposMock), para conferir tempo_ms e formato
const corpos: unknown[] = []
;(globalThis as unknown as { __corposMock: unknown[] }).__corposMock = corpos

export async function responderMock<T>(caminho: string, init?: RequestInit): Promise<T> {
  await esperar(250)
  const url = new URL(caminho, 'http://mock')
  const p = url.pathname
  const q = url.searchParams
  let r: unknown
  // ?fora na URL da página simula Trello e Anki fora do ar (o campo vira {"erro": ...})
  const fora = typeof location !== 'undefined' && location.search.includes('fora')
  if (p === '/api/hoje')
    r = fora ? { ...hoje, trello: { erro: 'TrelloIndisponivel: falha ao ler o board' }, anki: { erro: 'AnkiIndisponivel: coleção não encontrada' } } : hoje
  else if (p === '/api/aulas') {
    const busca = (q.get('busca') ?? '').toLowerCase()
    r = aulas
      .filter((a) => !busca || a.texto_md.toLowerCase().includes(busca))
      .map(({ texto_md: _t, id: _i, fase: _f, semana: _s, origem: _o, criado_em: _c, ...resumo }) => resumo satisfies AulaResumo)
  } else if (p.startsWith('/api/aulas/')) {
    const lista = aulas.filter((a) => a.data === decodeURIComponent(p.slice(11)))
    if (!lista.length) throw new ErroApi(404, 'nenhuma aula nesse dia')
    r = lista
  } else if (p === '/api/calendario') r = calendario(q.get('de')!, q.get('ate')!)
  else if (p === '/api/regras') r = regras
  else if (p === '/api/licoes') {
    const l = licaoMock()
    const exs = l.exercicios.filter((e) => e.tipo !== 'explicacao')
    const conta = (v: string) => exs.filter((e) => e.resultado?.veredito === v).length
    r = [{ id: l.id, data: l.data, titulo: l.titulo, status: l.status, total: exs.length, certos: conta('certo'), errados: conta('errado'), revisar: conta('revisar'), pendentes: exs.filter((e) => !e.resultado).length }] satisfies LicaoResumo[]
  } else if (p === '/api/licoes/atual' || p === '/api/licoes/1') r = licaoMock()
  else if (p.startsWith('/api/licoes/')) throw new ErroApi(404, 'lição não encontrada')
  else if (/^\/api\/exercicios\/\d+\/resposta$/.test(p) && init?.method === 'POST') {
    const corpo = JSON.parse(String(init.body))
    corpos.push({ exercicio: Number(p.split('/')[3]), ...corpo })
    r = responderExercicioMock(Number(p.split('/')[3]), corpo)
  } else throw new ErroApi(404, `mock sem rota: ${p}`)
  // cópia profunda: o React Query não pode segurar referência ao estado do mock
  return JSON.parse(JSON.stringify(r)) as T
}
