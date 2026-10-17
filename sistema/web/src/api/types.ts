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
export interface RenderProducao { minimo: number; dicas: string[] }

// corpo da resposta, por tipo
export interface RespostaEscolha { opcao: string }
export interface RespostaAcharErro { segmento: number }
export interface RespostaLigar { pares: [string, string][] }
export interface RespostaOrdenar { pecas: string[] }
export interface RespostaCompletar { lacunas: string[] }
export interface RespostaTexto { texto: string }
export interface RespostaProducao { frases: string[] }

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
