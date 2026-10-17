// Tipos da API HTTP — espelham sistema/DESIGN.md §9 e §10.
// O formato de /api/hoje é o do hoje() do MCP (DESIGN §6), que o §10 referencia.

/** Fonte externa fora do ar: o campo dela vem assim e o resto da resposta segue (DESIGN §6). */
export interface ErroFonte {
  erro: string
}

export function ehErro(x: unknown): x is ErroFonte {
  return typeof x === 'object' && x !== null && 'erro' in x && typeof (x as ErroFonte).erro === 'string'
}

export type TipoAula = 'completa' | 'parcial' | 'sem_mesa'

// ------------------------------------------------------------------ /api/hoje

export interface UltimaAula {
  data: string
  dia: number | null
  tipo: TipoAula
  titulo: string | null
  deixou_para_hoje: string | null
  dias_atras: number | null
}

export interface PadraoAberto {
  id: number
  categoria: string
  descricao: string
  aberto_em: string
}

export interface PendenciaTrello {
  nome: string
  vence: string | null
  vencido: boolean
  url: string | null
}

export interface ChecklistSemana {
  nome: string
  /** "5/7" */
  feitos: string
  faltam: string[]
}

export interface CardSemana {
  card: string
  checklists: ChecklistSemana[]
}

export interface ResumoTrello {
  pendencias_7_dias: PendenciaTrello[]
  semana_atual: CardSemana[]
  avisos_jlpt: { nome: string; url: string | null }[]
}

export interface ResumoAnki {
  leitura: string
  hoje: { cartoes: number; minutos: number }
  ontem: { cartoes: number; minutos: number }
  fila_atrasados: number
  alerta_fila: string | null
  retencao_30d: number | null
  alerta_retencao: string | null
  /** "情報 (12x)" */
  em_loop: string[]
  bandeira: string[]
}

export interface Hoje {
  agora: string
  dia_de_estudo: string
  dia_do_plano: number
  streak: { atual_ate_ontem: number; recorde: number }
  ultima_aula: UltimaAula | null
  plano_de_hoje: string | null
  proximos: string[]
  lembrete_abertura: { texto: string; de: string } | null
  padroes_abertos: PadraoAberto[]
  avisos: string[]
  trello: ResumoTrello | ErroFonte
  anki: ResumoAnki | ErroFonte
}

// ------------------------------------------------------------------ /api/aulas

export interface AulaResumo {
  data: string
  dia_plano: number | null
  tipo: TipoAula
  titulo: string | null
  inicio: string | null
  minutos: number | null
  verif_ok: number | null
  verif_total: number | null
  prod_ok: number | null
  prod_total: number | null
}

export interface AulaCompleta extends AulaResumo {
  id: number
  fase: number | null
  semana: number | null
  texto_md: string
  origem: 'migracao' | 'mcp'
  criado_em: string
}

// ------------------------------------------------------------------ /api/calendario

export interface AulaDoDia {
  tipo: TipoAula
  titulo: string | null
  dia_plano: number | null
  verif_ok: number | null
  verif_total: number | null
  prod_ok: number | null
  prod_total: number | null
}

export interface TrajetoDoDia {
  anki_cartoes: number | null
  anki_minutos: number | null
  /** 1 = ouviu, 0 = não ouviu, null = não informado */
  audio: 0 | 1 | null
}

export type StatusLicao = 'aberta' | 'concluida'

export interface DiaCalendario {
  data: string
  aulas: AulaDoDia[]
  trajeto: TrajetoDoDia | null
  plano: string | null
  licoes: { id: number; titulo: string; status: StatusLicao }[]
}

export interface EventoTrello {
  nome: string
  vence: string
  url: string | null
  concluido: boolean
  lista: string
}

export interface Calendario {
  dias: DiaCalendario[]
  eventos_trello: EventoTrello[] | ErroFonte
}

// ------------------------------------------------------------------ exercícios (§9)

export type TipoExercicio =
  | 'escolha'
  | 'achar_erro'
  | 'ligar'
  | 'ordenar'
  | 'completar'
  | 'digitar'
  | 'conjugar'
  | 'ouvir'
  | 'producao'

export type Bloco = 'aquecimento' | 'verificacao' | 'producao' | 'revisao'

export type Veredito = 'certo' | 'errado' | 'revisar'

// render: o que o navegador recebe (sem gabarito, já embaralhado)
export interface RenderEscolha { opcoes: string[] }
export interface RenderAcharErro { segmentos: string[] }
export interface RenderLigar { esquerda: string[]; direita: string[] }
export interface RenderOrdenar { pecas: string[] }
export type ParteCompletar = string | { lacuna: number; opcoes?: string[] }
export interface RenderCompletar { partes: ParteCompletar[] }
/** a dica é opcional: sem ela o servidor manda {} */
export interface RenderDigitar { dica?: string | null }
export interface RenderConjugar { verbo: string; leitura?: string; forma: string }
/** ouvir (§12.3): nunca vem o texto falado, que é a resposta. audio = null só se o mp3 não foi gravado. */
export interface RenderOuvir { modo: 'ditado' | 'escolha'; audio: string | null; opcoes?: string[] }
export interface RenderProducao { minimo: number; dicas: string[] }

// corpo da resposta, por tipo
export interface RespostaEscolha { opcao: string }
export interface RespostaAcharErro { segmento: number }
export interface RespostaLigar { pares: [string, string][] }
export interface RespostaOrdenar { pecas: string[] }
export interface RespostaCompletar { lacunas: string[] }
export interface RespostaTexto { texto: string }
export interface RespostaProducao { frases: string[] }
/** ditado manda `texto`, compreensão manda `opcao`; `toques` = quantas vezes tocou (informativo) */
export type RespostaOuvir = ({ texto: string } | { opcao: string }) & { toques?: number }

// detalhe da correção, por tipo (§10)
export interface ParLigar { esquerda: string; escolhida: string | null; certa: string; ok: boolean }
export interface DetalheLigar { pares: ParLigar[] }
export interface DetalheCompletar { lacunas: boolean[] }
export interface DetalheOrdenar { montada: string }
export interface OpDiff { op: 'igual' | 'faltou' | 'sobrou'; texto: string }
export interface DetalheTexto { diff: OpDiff[]; comparado_com: string }
export interface DetalheAcharErro { errado: number; correcao: string }
/** escolha e produção não têm detalhe: o servidor manda {} */
export type DetalheVazio = Record<string, never>

/** Mapa tipo → (render, resposta, detalhe): mantém widget, corpo e correção amarrados pelo tipo. */
export interface PorTipo {
  escolha: { render: RenderEscolha; resposta: RespostaEscolha; detalhe: DetalheVazio }
  achar_erro: { render: RenderAcharErro; resposta: RespostaAcharErro; detalhe: DetalheAcharErro }
  ligar: { render: RenderLigar; resposta: RespostaLigar; detalhe: DetalheLigar }
  ordenar: { render: RenderOrdenar; resposta: RespostaOrdenar; detalhe: DetalheOrdenar }
  completar: { render: RenderCompletar; resposta: RespostaCompletar; detalhe: DetalheCompletar }
  digitar: { render: RenderDigitar; resposta: RespostaTexto; detalhe: DetalheTexto }
  conjugar: { render: RenderConjugar; resposta: RespostaTexto; detalhe: DetalheTexto }
  /** detalhe: DetalheTexto no ditado; {} na compreensão */
  ouvir: { render: RenderOuvir; resposta: RespostaOuvir; detalhe: DetalheTexto | DetalheVazio }
  producao: { render: RenderProducao; resposta: RespostaProducao; detalhe: DetalheVazio }
}

export type RespostaDe<T extends TipoExercicio> = PorTipo[T]['resposta']
export type DetalheDe<T extends TipoExercicio> = PorTipo[T]['detalhe']

/** A primeira resposta (a que conta), como GET /api/licoes/{id} devolve. */
export interface Resultado<T extends TipoExercicio = TipoExercicio> {
  veredito: Veredito
  resposta: RespostaDe<T>
  /** sempre um texto pronto para mostrar ("猫は部屋にいます"; "日本を → 日本に"); vazio na produção */
  gabarito: string
  explicacao: string | null
  /** Partial: escolha e produção vêm com {}, e uma resposta antiga pode não ter detalhe */
  detalhe: Partial<DetalheDe<T>>
  /** a correção do tutor (markdown), ao fechar um 'revisar' */
  correcao: string | null
}

interface ExercicioBase<T extends TipoExercicio> {
  id: number
  ordem: number
  bloco: Bloco
  tipo: T
  categoria: string | null
  enunciado: string
  render: PorTipo[T]['render']
  resultado: Resultado<T> | null
}

/** União discriminada por `tipo`: um switch em ex.tipo estreita render e resultado juntos. */
export type Exercicio = { [T in TipoExercicio]: ExercicioBase<T> }[TipoExercicio]
export type ExercicioDe<T extends TipoExercicio> = ExercicioBase<T>

export interface Licao {
  id: number
  data: string
  titulo: string
  status: StatusLicao
  exercicios: Exercicio[]
}

export interface LicaoResumo {
  id: number
  data: string
  titulo: string
  status: StatusLicao
  total: number
  certos: number
  errados: number
  revisar: number
  pendentes: number
}

export interface CorpoResposta<T extends TipoExercicio = TipoExercicio> {
  resposta: RespostaDe<T>
  tempo_ms: number
}

/** POST /api/exercicios/{id}/resposta */
export interface Correcao<T extends TipoExercicio = TipoExercicio> {
  veredito: Veredito
  gabarito: string
  explicacao: string | null
  detalhe: Partial<DetalheDe<T>>
  /** a API também diz se esta resposta contou (só a primeira conta); não está no contrato do §10 */
  contou?: boolean
}

// ------------------------------------------------------------------ Fase 3 (DESIGN §12)

export interface Padrao {
  id: number
  categoria: string
  descricao: string
  status: 'aberto' | 'resolvido'
  aberto_em: string
  resolvido_em: string | null
  nota: string | null
}

export interface ErroRegistrado {
  data: string
  bloco: 'abertura' | 'verificacao' | 'producao' | 'diagnostico' | 'anki' | 'outro'
  categoria: string
  escrito: string | null
  correto: string | null
  porque: string | null
}

/** GET /api/erros?dias=&categoria= (o mesmo do erros() do MCP; no máximo 100, mais novo primeiro) */
export interface Erros {
  desde: string
  por_categoria: Record<string, number>
  erros: ErroRegistrado[]
}

/** GET /api/erros/painel?dias=90 (§12.1) */
export interface ErrosPainel {
  desde: string
  /** o erro mais antigo do banco: o registro erro a erro só começou em 16/10; antes disso "nenhum erro" não quer dizer nada */
  primeiro_erro: string | null
  total: number
  /** grupo = prefixo antes do ':' ('particula:wo' → 'particula') */
  por_categoria: { categoria: string; grupo: string; n: number; ultimo: string }[]
  /** semana = a segunda-feira (AAAA-MM-DD) */
  por_semana: { semana: string; grupo: string; n: number }[]
  por_bloco: Partial<Record<ErroRegistrado['bloco'], number>>
  /** só a primeira resposta conta; taxa_erro = errados / (certos + errados), null se nada fechado */
  tipos_exercicio: {
    tipo: TipoExercicio
    respondidos: number
    certos: number
    errados: number
    revisar: number
    taxa_erro: number | null
  }[]
  padroes: { abertos: Padrao[]; resolvidos: Padrao[] }
}

/** GET /api/registro?busca= — o log herdado de pontos_fracos (antes do sistema) */
export interface RegistroAntigo {
  data: string | null
  texto: string
}

export interface BaralhoAnki {
  baralho: string
  total: number
  novos: number
  devidos: number
  aprendendo: number
  suspensos: number
}

/** o mesmo do anki() do MCP */
export interface StatusAnki {
  fonte: { fonte: string; rotulo: string; idade_dias: number }
  baralhos: BaralhoAnki[]
  fila_atrasados: number
  alerta_fila: string | null
  /** 7 itens, do mais antigo (dias_atras 6) para hoje (0) */
  ultimos_7_dias: { dias_atras: number; cartoes: number; minutos: number }[]
  retencao_30d: number | null
  alerta_retencao: string | null
  botoes_30d_pct: { again: number; hard: number; good: number; easy: number }
  travam: { frente: string; lapses: number; baralho: string }[]
  em_loop: { frente: string; again_7d: number; baralho: string }[]
  bandeira: { frente: string; baralho: string }[]
}

export interface GraficosAnki {
  /** as 12 últimas semanas desde o início do plano; semana = segunda-feira */
  retencao_semanal: { semana: string; revisoes: number; acertos: number; pct: number }[]
  /** jovem = intervalo < 21 dias; maduro = ≥ 21 */
  maturidade: { novos: number; aprendendo: number; jovens: number; maduros: number; suspensos: number }
  /** 14 dias a partir de hoje; o de hoje inclui os atrasados */
  previsao: { data: string; devidos: number }[]
}

export interface DiaAnki {
  data: string
  cartoes: number
  minutos: number
  /** 1 = ouviu, 0 = não ouviu, null = não informado */
  audio: 0 | 1 | null
}

/** GET /api/anki/painel (§12.2) */
export interface AnkiPainel {
  status: StatusAnki | ErroFonte
  graficos: GraficosAnki | ErroFonte
  /** todo dia desde 03/08 até hoje, sem buraco */
  por_dia: DiaAnki[]
  /** presente quando o Anki não abriu e por_dia veio do banco */
  fonte_por_dia?: string
}

export interface Acento {
  leitura: string
  /** posição da queda de tom (0 = heiban) */
  quedas: number[]
  padroes: string[]
}

export interface SentidoKotoba {
  classe: string[]
  misc: string[]
  pt: string[]
  /** true = tradução automática para o português (mostrar como tal) */
  pt_auto: boolean
  en: string[]
}

export interface VerbeteKotoba {
  ent_seq: number
  palavra: string
  grafia_kanji: string | null
  leitura: string
  glosas_pt: string[]
  glosas_pt_auto: string[]
  glosas_en: string[]
  /** 5 = N5 … 1 = N1 */
  jlpt: number | null
  comum: boolean
  classe: string[]
  acento: Acento | null
  casamento: string
  sentido_casado: number | null
  usual_em_kana: boolean
  sentidos: SentidoKotoba[]
  /** a palavra (ou a leitura) é um campo inteiro de alguma nota do Anki; null = o Anki não abriu */
  tem_cartao: boolean | null
}

/** GET /api/kotoba/buscar?q= (§12.4); fonte fora do ar = ErroFonte */
export type BuscaKotoba = { resultados: VerbeteKotoba[] } | ErroFonte

/** GET /api/kotoba/kanji/{literal}; 404 se não houver */
export interface KanjiKotoba {
  kanji: string
  on: string[]
  kun: string[]
  significados_pt: string[]
  significados_pt_auto: boolean
  significados_en: string[]
  /** escala nova, como no verbete: 5 = N5 … 1 = N1 */
  jlpt: number | null
  tracos: number | null
  serie: number | null
  frequencia: number | null
  radical: {
    numero: number
    glifo: string
    nome: string
    romaji: string
    significado_pt: string
    /** a forma do radical dentro do kanji (氵 de 海, 訁 de 話); posicao = 'hen', 'tsukuri'… */
    variante: { glifo: string; nome: string; posicao: string; significado_pt: string } | null
  } | null
  componentes: { glifo: string; nome_pt: string }[]
  /** a frase de memorização do Kotoba (markdown com **negrito**) */
  mnemonico: { significado: string; leitura_kana: string; leitura_frase: string } | null
}

export interface ConsultaKotoba {
  tipo: 'query' | 'entry' | 'kanji'
  /** "持つ · segurar" (entry), o texto buscado (query) ou o kanji */
  rotulo: string
  consulta: string | null
  kanji: string | null
  /** ISO local sem fuso: '2026-10-17T02:18:37' (pode ser a madrugada do dia seguinte) */
  quando: string
  ent_seq: number | null
  /** só em 'entry' */
  palavra: string | null
  leitura?: string | null
  tem_cartao?: boolean | null
}

export interface CandidataCartao {
  palavra: string
  leitura: string | null
  rotulo: string
  vezes: number
  ultima: string
}

/** GET /api/kotoba/historico?dias=30 (§12.4); dias do mais novo para o mais antigo */
export type HistoricoKotoba =
  | { dias: { data: string; consultas: ConsultaKotoba[] }[]; sem_cartao: CandidataCartao[]; aviso?: string }
  | ErroFonte

export interface ItemListaKotoba {
  tipo: 'entry' | 'kanji'
  ref: string | number
  palavra: string | null
  leitura: string | null
  glosa_pt: string | null
  nota: string | null
  adicionado: string
}

/** GET /api/kotoba/listas */
export type ListasKotoba = { id: number; nome: string; favoritos: boolean; total: number; itens: ItemListaKotoba[] }[] | ErroFonte
