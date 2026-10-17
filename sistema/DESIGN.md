# Sistema de estudo — Documento de Design

> Fonte da verdade do `sistema/`. Mudou o contrato (schema, ferramenta MCP, rota)? Muda aqui primeiro.
> Criado em 17/10/2026, de madrugada, a pedido dele: "um sistema para que você consiga dar as aulas todos os dias, verificar o Trello, olhar aulas anteriores, ter um calendário".

## 0. Para que serve

Juntar num lugar só o que hoje está espalhado — Trello, Anki, Kotoba, `diario.md`, `estado.json`, `curriculo.md` — e dar ao tutor (Claude Code) **consultas** no lugar de **arquivos inteiros**.

Dois clientes, um núcleo:

```
┌──────────────┐  MCP (stdio)        ┌────────────────────────────────┐
│ Claude Code  │ ──────────────────▶ │  japones (Python)              │
│  /estudo     │                     │  estudo.db (SQLite)            │
└──────────────┘                     │  fontes: Anki · Trello ·       │
┌──────────────┐  HTTP (localhost)   │  Kotoba · diário · currículo   │
│ Painel web   │ ──────────────────▶ │  API (FastAPI) — Fase 2        │
│ React + Vite │                     └────────────────────────────────┘
└──────────────┘
```

**O que o sistema NÃO é:** um substituto da hora de mesa. A aula continua acontecendo no terminal, com a skill `/estudo`. Construir o sistema nunca ocupa o horário da mesa.

## 1. Decisões que fecham o escopo (17/10/2026)

| Decisão | Valor | Por quê |
|---|---|---|
| Onde roda | só no PC, `localhost` | o Anki só é alcançável no PC (AnkiConnect com o Anki aberto; AnkiWeb não tem API). No celular, só o Anki |
| Trello | **continua principal** para pendências, cobranças e cronograma | o sistema lê e linka, não substitui |
| Aulas | no terminal (Claude Code, plano dele) | chat no painel exigiria API paga por uso |
| Núcleo | Python 3.13 + FastAPI + SQLite | as ferramentas de `tools/` já são Python |
| Front (Fase 2) | React + Vite + TypeScript, Tailwind + shadcn/ui, TanStack Query, FullCalendar, Recharts | local, sem SSR: Next.js não acrescenta nada |
| Dados privados | `~/.local/share/japones/estudo.db` | o repositório é público; o código vai para o GitHub, a vida dele não |

## 2. Layout

```
sistema/
  DESIGN.md            este documento
  AGENTS.md            instruções para agentes de código (o CLAUDE.md só importa este)
  pyproject.toml
  mcp.sh               lançador do servidor MCP (usado pelo .mcp.json da raiz)
  japones/
    config.py          caminhos, fuso, regra das 04:00
    db.py              conexão, migrações por PRAGMA user_version
    schema.sql         DDL do estudo.db
    dominio.py         dia de estudo, dia do plano, streak
    fontes/
      anki.py          leitura da coleção (cópia) — reaproveita tools/anki_status.py
      trello.py        leitura do board — reaproveita tools/trello.py
      kotoba.py        dicionário e histórico do Kotoba — SÓ LEITURA
      curriculo.py     tabelas de plano/curriculo.md
      diario.py        entradas de progresso/diario.md
    migracao.py        importação única do histórico (diário, pontos_fracos, Anki)
    mcp_server.py      ferramentas do tutor
  tests/
  web/                 painel (Fase 2)
```

## 3. Quem manda em quê

| Fonte | Dono | O sistema |
|---|---|---|
| Trello | Trello | lê; escreve só pelo `tools/trello.py` (pendência, marcar áudio) |
| Anki | Anki | **só lê, de uma cópia** (o `anki_status.py` já faz assim) |
| Kotoba (`dictionary/`) | o app | **só lê**: dicionário com `mode=ro&immutable=1`, `user.db` de uma cópia. Nunca escreve no banco de outro app |
| `estudo.db` | o sistema | lê e escreve: aulas, trajeto diário, erros, padrões, notas |
| `progresso/diario.md` | o sistema (append-only) | `registrar_aula` acrescenta a entrada; o texto é a narrativa |
| `progresso/estado.json` | transição | perde os logs (horários, `pontos_fracos`, notas de trajeto), que vão para o banco; fica com o que muda devagar (`meta`, `metodo_acordado`, `projeto_japao`) |
| `plano/curriculo.md` | o tutor | o sistema só lê; é o calendário do que vem |

## 4. `estudo.db`

### 4.1 DDL (`japones/schema.sql`)

Ver o arquivo; resumo:

| Tabela | Uma linha é | Chave |
|---|---|---|
| `aula` | uma entrada do diário (inclui dias **sem mesa**) | `id`; `data` não é única (08/08 e 14/09 tiveram duas sessões) |
| `trajeto` | um dia de trajeto: Anki (cartões, minutos) e áudio | `data` |
| `erro` | um erro corrigido, com categoria | `id` |
| `padrao` | um padrão em vigília (o "topo de `pontos_fracos`") | `id` |
| `registro` | o log livre herdado de `pontos_fracos` (busca por texto) | `id` |
| `nota` | chave/valor: `lembrete_abertura` e afins | `chave` |

Datas são sempre o **dia de estudo** (`AAAA-MM-DD`, regra das 04:00, §5).

### 4.2 Categorias de erro

Texto livre com prefixo, para o painel agrupar. Lista recomendada (a ferramenta `categorias()` devolve as já usadas):

`particula:ni-de` · `particula:wo` · `particula:wa-ga` · `particula:posicao` · `particula:outra` · `forma-te` · `forma-ta` · `conjugacao` · `adjetivo:familia` · `iru-aru` · `kana:dakuten` · `kana:vogal-longa` · `kana:sokuon` · `kana:troca` · `katakana` · `leitura-kanji` · `vocabulario` · `sentido` · `registro` · `ordem` · `outro`

`gramatica:<tema>` para um ponto de gramática específico (`gramatica:experiencia`, `gramatica:mou-mada`, `gramatica:proibicao`…) — o tema é o ponto ensinado, para o painel mostrar quais aulas não fixaram.

## 5. Regras de domínio (`dominio.py`)

- **Dia de estudo:** o dia vira às **04:00** (mesmo relógio do Anki). `dia_de_estudo(01:27 de 17/10) = 16/10`.
- **Dia do plano de hoje:** maior `dia_plano` entre as aulas completas/parciais + 1.
- **Streak:** dias de estudo **consecutivos** com aula completa ou parcial, terminando hoje ou ontem. Duas sessões no mesmo dia contam um dia. Recorde = a maior sequência da história.
- **Plano do dia:** a **última** linha de `curriculo.md` cuja data é a de hoje (o currículo é replanejado acrescentando tabelas; a linha mais nova vence).

## 6. Ferramentas MCP (`mcp_server.py`) — contrato

Toda ferramenta devolve JSON. **Nenhuma fonte externa derruba uma ferramenta:** se o Trello, o Anki ou o Kotoba falharem, o campo vem como `{"erro": "..."}` e o resto segue — a mesma regra da skill ("nenhuma ferramenta pode ser pré-requisito da hora de estudo").

| Ferramenta | O que devolve / faz |
|---|---|
| `hoje()` | o Passo 0 inteiro numa chamada: data e hora, dia de estudo, dia do plano, streak e recorde, última aula, plano do dia, `lembrete_abertura`, padrões abertos, pendências do Trello (vencidas e da semana), checklists da semana, resumo do Anki |
| `aulas(ultimas, busca, desde)` | lista resumida (sem o texto) |
| `aula(data)` | a(s) entrada(s) completa(s) do dia |
| `erros(categoria, dias)` | erros recentes + contagem por categoria |
| `padroes(status)` | padrões em vigília |
| `anki()` | o status completo do Anki em dados |
| `trello()` | o board em dados |
| `dicionario(termo)` / `kanji(literal)` | verificação pelo banco do Kotoba |
| `consultas_kotoba(data)` | o que ele procurou no Kotoba naquele dia de estudo |
| `registrar_aula(...)` | grava a aula **e** acrescenta a entrada no `diario.md` |
| `registrar_trajeto(...)` | grava o trajeto do dia (Anki e áudio) |
| `registrar_erros(data, erros)` | grava os erros corrigidos, categorizados |
| `abrir_padrao(...)` / `resolver_padrao(id, nota)` | ciclo de vida dos padrões |
| `definir_nota(chave, valor)` | `lembrete_abertura` e afins |
| `backup()` | copia `estudo.db` (API de backup do SQLite), `diario.md` e `estado.json` para `~/.local/share/japones/backup-progresso/` |

## 7. Fases e critério de pronto

1. **Núcleo + MCP.** Pronto quando: a migração importa as 77 entradas do diário e o histórico do Anki; `hoje()` responde em menos de 3 s com as fontes no ar; a `/estudo` usa `hoje()` no Passo 0 e as ferramentas de registro no Passo 4; os testes passam.
2. **Painel + exercícios** (§9 a §11): Hoje, Aula (exercícios), Calendário, Aulas. API FastAPI sobre o mesmo núcleo; o build do React servido pelo FastAPI; serviço `systemd --user`. Pronto quando: o tutor cria uma lição pelo MCP com os 8 tipos, ele faz no navegador com correção na hora, e o tutor lê o resultado e corrige a produção pelo MCP.
3. **Erros, Anki, Kotoba** no painel.
4. **No repositório do Kotoba** (decisão dele): gravar o placar do "Treinar formas" num `drill_result` do `user.db`, para o painel mostrar a taxa de acerto por forma.

## 8. Registro de decisões

- **17/10** — `diario.md` continua existindo: é a narrativa, e é o que ele lê. O banco guarda a estrutura (placar, horário, erros) e uma cópia do texto para busca.
- **17/10** — `pontos_fracos` (123 entradas, 41 KB) não é reclassificado à força na migração: vai inteiro para `registro`, com a data, e os **erros categorizados começam a valer daqui para frente**. Os padrões abertos hoje são semeados à mão.
- **17/10** — SDK do MCP na versão 2 (`from mcp.server import MCPServer`); a 1.x chamava a classe de `FastMCP`.
- **17/10** — Exercícios no painel, pedido dele: "tipos diferentes de exercícios — ligar pontos, colocar em ordem, escolher o certo, falar qual está errado, digitar a frase, completar a frase — você monta as aulas de acordo com a necessidade, sempre variando os tipos, mas utilizando todos". O tutor continua ensinando no chat; o painel é onde ele **faz** os exercícios. O sorteio dos tipos (§9.4) garante variedade sem deixar tipo nenhum de fora.

- **17/10** — FullCalendar fixado no conjunto 6.1.22: o `@fullcalendar/react` mais novo do npm é 7.x, mas daygrid e interaction só existem na 6.1.22, e as duas versões não conversam.
- **17/10** — Fase 2 entregue: motor de exercícios, 4 ferramentas MCP, API como serviço `systemd --user` (`japones-painel`) e o painel. A primeira lição (revisão do dia 68, os 8 tipos) foi respondida numa CÓPIA do banco para testar o fluxo inteiro; o banco real ficou intacto.

## 9. Exercícios [CONTRATO]

### 9.1 Modelo

Uma **lição** (`licao`) é a lista de exercícios de um dia de estudo, criada pelo tutor via MCP. Cada **exercício** tem campos comuns e um `dados` próprio do tipo, **com o gabarito**, que nunca sai do servidor: o navegador recebe só o `render` (§9.2), já embaralhado.

Campos comuns de um exercício:

| Campo | Valor |
|---|---|
| `tipo` | `escolha` · `achar_erro` · `ligar` · `ordenar` · `completar` · `digitar` · `conjugar` · `producao` |
| `bloco` | `aquecimento` · `verificacao` · `producao` · `revisao` |
| `categoria` | categoria de erro (§4.2) que um erro neste exercício alimenta; opcional |
| `enunciado` | a instrução, em português (pode conter japonês) |
| `explicacao` | a regra em uma ou duas linhas, mostrada depois da resposta (pedido dele em 16/10: toda correção reexplica a regra) |
| `dados` | por tipo, §9.2 |

### 9.2 Tipos: `dados` (servidor) → `render` (navegador) → resposta → correção

| Tipo | `dados` (com gabarito) | `render` | corpo da resposta | Correção |
|---|---|---|---|---|
| `escolha` | `{"opcoes": [..], "correta": "に"}` | `{"opcoes": [..]}` embaralhadas | `{"opcao": "に"}` | automática |
| `achar_erro` | `{"segmentos": ["日本を","行ったことが","ありません"], "errado": 0, "correcao": "日本に"}` | `{"segmentos": [..]}` na ordem da frase | `{"segmento": 0}` | automática |
| `ligar` | `{"pares": [["書く","書いて"], ..]}` (3 a 6; lados sem repetição) | `{"esquerda": [..], "direita": [..]}` cada lado embaralhado | `{"pares": [["書く","書いて"], ..]}` | automática; certo só com todos os pares |
| `ordenar` | `{"pecas": ["猫は","部屋に","います"], "aceitas": [[..],[..]], "distratores": ["で"]}` (`aceitas` padrão = `[pecas]`; `distratores` opcional, peças que sobram) | `{"pecas": [..]}` embaralhadas, nunca na ordem certa | `{"pecas": [..]}` na ordem escolhida | automática: tem de ser igual a uma das `aceitas` |
| `completar` | `{"texto": "猫{0}部屋{1}います", "lacunas": [{"aceitas": ["は","が"], "opcoes": ["は","が","に","で","を"]}, {"aceitas": ["に"]}]}` (lacuna sem `opcoes` = digitada) | `{"partes": ["猫", {"lacuna": 0, "opcoes": [..]}, "部屋", {"lacuna": 1}, "います"]}` | `{"lacunas": ["は","に"]}` | automática, lacuna por lacuna |
| `digitar` | `{"aceitas": ["日本に行ったことがありません", ..], "dica": "..."}` | `{"dica": "..."}` | `{"texto": "..."}` | bateu com uma aceita → `certo`; senão `revisar` (o tutor decide), com o diff contra a aceita mais parecida |
| `conjugar` | `{"verbo": "撮る", "leitura": "とる", "forma": "forma て", "aceitas": ["撮って","とって"]}` | `{"verbo", "leitura", "forma"}` | `{"texto": "..."}` | automática (conjunto fechado: as `aceitas` trazem kanji **e** kana) |
| `producao` | `{"minimo": 3, "dicas": [..]}` | igual | `{"frases": [..]}` | sempre `revisar`: o tutor corrige pelo MCP |

**Normalização** antes de comparar texto: NFKC, sem espaços, sem `。、.,!?！？`. Katakana e hiragana **não** se equivalem (trocar é erro de `katakana`/`kana:troca`).

**Veredito:** `certo` · `errado` · `revisar`. Só a **primeira** resposta conta para placar e para a tabela `erro`; dá para responder de novo para praticar.

**Erro automático:** a primeira resposta `errado` de um exercício grava uma linha em `erro` (`categoria` do exercício ou `outro`; `escrito` = a resposta; `correto` = o gabarito; `porque` = a explicação; bloco `aquecimento`→`abertura`, `revisao`→`outro`). Um `revisar` corrigido como `errado` pelo tutor também grava.

### 9.3 DDL (esquema 2)

```sql
CREATE TABLE licao (id INTEGER PRIMARY KEY, data TEXT NOT NULL, titulo TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'aberta' CHECK (status IN ('aberta','concluida')),
  criada_em TEXT NOT NULL DEFAULT (datetime('now','localtime')), concluida_em TEXT);
CREATE TABLE exercicio (id INTEGER PRIMARY KEY, licao_id INTEGER NOT NULL REFERENCES licao(id) ON DELETE CASCADE,
  ordem INTEGER NOT NULL, bloco TEXT NOT NULL, tipo TEXT NOT NULL, categoria TEXT,
  enunciado TEXT NOT NULL, dados TEXT NOT NULL, explicacao TEXT);
CREATE TABLE resposta (id INTEGER PRIMARY KEY, exercicio_id INTEGER NOT NULL REFERENCES exercicio(id) ON DELETE CASCADE,
  resposta TEXT NOT NULL, veredito TEXT NOT NULL CHECK (veredito IN ('certo','errado','revisar')),
  detalhe TEXT, correcao TEXT, tempo_ms INTEGER, criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')));
```

A lição fica `concluida` quando todo exercício tem resposta.

### 9.4 Sorteio dos tipos (`planejar_tipos`)

"Sempre variando, mas utilizando todos." Peso de cada tipo = 1 + **2** se não apareceu nas últimas 2 lições + **2 × taxa de erro** do tipo nos últimos 30 dias. Sorteio ponderado sem passar de 2 exercícios do mesmo tipo por lição; `producao` entra sempre (regra 4 do CLAUDE.md: produção ativa todo dia). O tutor recebe a sequência e escreve o conteúdo de cada exercício a partir da necessidade do dia (padrões abertos, erros recentes, conteúdo novo).

### 9.5 Ferramentas MCP novas

| Ferramenta | Faz |
|---|---|
| `planejar_tipos(n, semente)` | a sequência sorteada (§9.4) e o porquê de cada peso |
| `criar_licao(titulo, exercicios, data)` | valida cada exercício pelo tipo, grava, devolve `id` e o link do painel |
| `resultado_licao(id)` | resumo da lição (padrão: a mais recente): veredito, resposta e gabarito de cada exercício, e os `revisar` pendentes |
| `corrigir_exercicio(exercicio_id, veredito, correcao)` | fecha um `revisar` (`certo`/`errado`) com a correção, que aparece no painel |

## 10. API HTTP (`japones/api.py`, `127.0.0.1:8787`) [CONTRATO]

Só escuta em `127.0.0.1`. JSON em tudo; datas `AAAA-MM-DD`.

| Rota | Devolve |
|---|---|
| `GET /api/hoje` | o mesmo de `hoje()` do MCP |
| `GET /api/aulas?ultimas=30&busca=` | aulas resumidas, mais nova primeiro |
| `GET /api/aulas/{data}` | as entradas do dia, com `texto_md` |
| `GET /api/calendario?de=&ate=` | `{"dias": [{"data", "aulas": [{tipo, titulo, dia_plano, verif_ok, verif_total, prod_ok, prod_total}], "trajeto": {anki_cartoes, anki_minutos, audio} \| null, "plano": str \| null, "licoes": [{id, titulo, status}]}], "eventos_trello": [{nome, vence, url, concluido, lista}]}` (Trello pode vir como `{"erro": ...}`) |
| `GET /api/licoes?ultimas=20` | `[{id, data, titulo, status, total, certos, errados, revisar, pendentes}]` |
| `GET /api/licoes/atual` | a lição aberta mais recente (ou a mais recente) renderizada; 404 se não houver |
| `GET /api/licoes/{id}` | `{id, data, titulo, status, exercicios: [{id, ordem, bloco, tipo, categoria, enunciado, render, resultado}]}`; `resultado` é `null` ou `{veredito, resposta, gabarito, explicacao, detalhe, correcao}` da primeira resposta |
| `POST /api/exercicios/{id}/resposta` | corpo `{"resposta": {...§9.2}, "tempo_ms": 1234}` → `{veredito, gabarito, explicacao, detalhe}` |
| `GET /api/erros?dias=30` | o mesmo de `erros()` do MCP |
| `GET /` e rotas do SPA | `web/dist/index.html` (o build do React) |

`detalhe` por tipo: `ligar` → `{"pares": [{"esquerda", "escolhida", "certa", "ok"}]}`; `completar` → `{"lacunas": [true, false]}`; `ordenar` → `{"montada": "..."}`; `digitar`/`conjugar` → `{"diff": [{"op": "igual"|"faltou"|"sobrou", "texto": "..."}], "comparado_com": "..."}`; `achar_erro` → `{"errado": 0, "correcao": "..."}`.

`gabarito` é sempre um texto pronto para mostrar ("猫は部屋にいます"; "日本を → 日本に").

## 11. Painel (`web/`) [CONTRATO de telas]

React + Vite + TypeScript, Tailwind + shadcn/ui, TanStack Query, React Router, FullCalendar, react-markdown, dnd-kit. Claro/escuro pelo sistema. Fonte japonesa da máquina (`Noto Sans CJK JP`).

| Rota | Tela |
|---|---|
| `/` | **Hoje**: dia do plano, streak e recorde; plano de hoje e o que a última aula deixou; lembrete de abertura; botão **Aula de hoje** (se houver lição); pendências do Trello com link (vencidas em vermelho); checklists da semana; Anki (hoje/ontem, fila, retenção, em loop); padrões abertos |
| `/aula` e `/aula/:id` | **Aula**: um exercício por vez, barra de progresso, correção na hora com a explicação, resumo no fim |
| `/calendario` | mês: cor do dia pelo tipo da aula (completa/parcial/sem mesa), plano, prazos do Trello, lições, ponto de áudio; clique abre o detalhe do dia |
| `/aulas` e `/aulas/:data` | histórico com busca; a entrada do diário renderizada |

**Entrada japonesa (IME):** ele digita com ibus-mozc. Enter durante a composição (`isComposing`) **nunca** envia nem avança.
