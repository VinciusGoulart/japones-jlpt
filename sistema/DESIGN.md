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
    schema2.sql        lições e exercícios (Fase 2) · schema3.sql: o tipo ouvir (Fase 3)
    schema4.sql        caderno de regras e o tipo explicacao (§13)
    schema5.sql        a segunda tentativa com dica e o deslize (§9.6, §13.2)
    regras.py          caderno de regras: agenda de revisão espaçada e importador (§13)
    exercicios.py      motor de exercícios: validação, render, correção, sorteio (§9)
    audio.py           mp3 do exercício ouvir, pelo edge-tts (§12.3)
    rede.py            DNS só IPv4 para trello.com e bing.com (o AAAA deste PC leva 5 s)
    painel.py          agregados das telas Erros, Anki e Kotoba (§12)
    migracao.py        importação única do histórico (diário, pontos_fracos, Anki)
    mcp_server.py      ferramentas do tutor
    api.py             API HTTP do painel (§10)
  tests/
  web/                 painel React (§11)
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
| `erro` | um erro corrigido, com categoria; desde o esquema 5, `exercicio_id` (o exercício do painel que gerou o erro) e `deslize` (§9.6) | `id` |
| `padrao` | um padrão em vigília (o "topo de `pontos_fracos`") | `id` |
| `registro` | o log livre herdado de `pontos_fracos` (busca por texto) | `id` |
| `nota` | chave/valor: `lembrete_abertura` e afins | `chave` |
| `regra` | uma regra de gramática ensinada, com a agenda de revisão (§13) | `id`; `slug` único |

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
| `hoje()` | o Passo 0 inteiro numa chamada: data e hora, dia de estudo, dia do plano, streak e recorde, última aula, plano do dia, `lembrete_abertura`, padrões abertos, `regras_vencidas` (`{"total": N, "proximas": [até 5 slugs]}`, §13), `avisos`, pendências do Trello (vencidas e da semana), checklists da semana, resumo do Anki. **Aviso da madrugada** (23/10): com o relógio **real** entre 01:00 e 03:59 e o dia do **calendário** de segunda a sexta (ele trabalha nesse dia), entra "Depois da 1h em véspera de trabalho: aula só de revisão (regras vencidas + produção curta, até 30 min); o conteúdo novo passa para a próxima sessão." — o resto do `hoje()` segue o dia de estudo (regra das 04:00) |
| `aulas(ultimas, busca, desde)` | lista resumida (sem o texto) |
| `aula(data)` | a(s) entrada(s) completa(s) do dia |
| `erros(categoria, dias)` | erros recentes, cada um com `deslize` (bool, §9.6) + `por_categoria` (todos os erros) e `deslizes_por_categoria` (só as categorias com deslize) |
| `padroes(status)` | padrões em vigília |
| `anki()` | o status completo do Anki em dados. `bandeira`: até 30 cartões `{frente, baralho, cor}`, roxa primeiro (no `hoje()`, a frente com a cor: `"程度 (roxa)"`). Combinado de 25/10: **roxa** = ele não assimila sentido e fala → lista para a análise na mesa; **laranja** = trocadilho do Kaishi falta ou está ruim → o tutor reescreve (pipeline em `~/Documentos/kaishi-pt`) e tira a bandeira |
| `trello()` | o board em dados |
| `dicionario(termo)` / `kanji(literal)` | verificação pelo banco do Kotoba |
| `consultas_kotoba(data)` | o que ele procurou no Kotoba naquele dia de estudo, e `sem_cartao`: as palavras abertas que não estão em nenhuma nota do Anki (§12.4) |
| `registrar_aula(...)` | grava a aula **e** acrescenta a entrada no `diario.md` |
| `registrar_trajeto(...)` | grava o trajeto do dia (Anki e áudio) |
| `registrar_erros(data, erros)` | grava os erros corrigidos, categorizados |
| `abrir_padrao(...)` / `resolver_padrao(id, nota)` | ciclo de vida dos padrões |
| `definir_nota(chave, valor)` | `lembrete_abertura` e afins |
| `backup()` | copia `estudo.db` (API de backup do SQLite), `diario.md` e `estado.json` para `~/.local/share/japones/backup-progresso/` |
| `regras(vencidas, limite)` / `regra(slug)` / `salvar_regra(...)` | o caderno de regras de gramática (§13.5) |

## 7. Fases e critério de pronto

1. **Núcleo + MCP.** Pronto quando: a migração importa as 77 entradas do diário e o histórico do Anki; `hoje()` responde em menos de 3 s com as fontes no ar; a `/estudo` usa `hoje()` no Passo 0 e as ferramentas de registro no Passo 4; os testes passam.
2. **Painel + exercícios** (§9 a §11): Hoje, Aula (exercícios), Calendário, Aulas. API FastAPI sobre o mesmo núcleo; o build do React servido pelo FastAPI; serviço `systemd --user`. Pronto quando: o tutor cria uma lição pelo MCP com os 8 tipos, ele faz no navegador com correção na hora, e o tutor lê o resultado e corrige a produção pelo MCP.
3. **Erros, Anki, Kotoba** no painel, e o exercício **ouvir** (§12). Pronto quando: as três telas mostram os dados reais; o tutor cria uma lição com o tipo `ouvir` e o mp3 toca no painel; os testes passam sem rede.
4. **No repositório do Kotoba** (decisão dele): gravar o placar do "Treinar formas" num `drill_result` do `user.db`, para o painel mostrar a taxa de acerto por forma.

## 8. Registro de decisões

- **17/10** — `diario.md` continua existindo: é a narrativa, e é o que ele lê. O banco guarda a estrutura (placar, horário, erros) e uma cópia do texto para busca.
- **17/10** — `pontos_fracos` (123 entradas, 41 KB) não é reclassificado à força na migração: vai inteiro para `registro`, com a data, e os **erros categorizados começam a valer daqui para frente**. Os padrões abertos hoje são semeados à mão.
- **17/10** — SDK do MCP na versão 2 (`from mcp.server import MCPServer`); a 1.x chamava a classe de `FastMCP`.
- **17/10** — Exercícios no painel, pedido dele: "tipos diferentes de exercícios — ligar pontos, colocar em ordem, escolher o certo, falar qual está errado, digitar a frase, completar a frase — você monta as aulas de acordo com a necessidade, sempre variando os tipos, mas utilizando todos". O tutor continua ensinando no chat; o painel é onde ele **faz** os exercícios. O sorteio dos tipos (§9.4) garante variedade sem deixar tipo nenhum de fora.

- **17/10** — FullCalendar fixado no conjunto 6.1.22: o `@fullcalendar/react` mais novo do npm é 7.x, mas daygrid e interaction só existem na 6.1.22, e as duas versões não conversam.
- **17/10** — Fase 3: o tipo `ouvir` entra em `TIPOS`, e o padrão de `planejar_tipos` passa de 8 para 9 (todos os tipos, uma vez cada). A tabela `exercicio` ganha o tipo no CHECK pelo esquema 3 (SQLite não altera CHECK: a tabela é refeita).
- **17/10** — `tem_cartao` (§12.4): a grafia casa com qualquer campo de nota; a **leitura** só com a frente de nota escrita em kana. Casar a leitura com qualquer campo marcava お酢 e 雄 como "tem cartão" porque o Kaishi tem おす como campo da nota de 押す (achado no teste da tela Kotoba).
- **17/10** — Registro antigo: "ANIMACIDADE 3/5 NA ESTREIA (31/08)" estava datado de 03/05, porque a migração lia o placar como data. Agora vale a primeira data que cai dentro do plano (`migracao._data_do_registro`); o registro foi reimportado.
- **17/10** — Fase 3 entregue: telas Erros, Anki e Kotoba, o tipo `ouvir` (testado numa CÓPIA do banco, porta 8788, com mp3 de verdade) e o esquema 3. Os gráficos usam 5 famílias de erro em vez dos grupos do §4.2 (15 cores numa pilha não se leem); a tabela de categorias mantém o detalhe.
- **23/10** — Caderno de regras (§13), pedido dele. Diagnóstico: ele esquece regras antigas (てもいいですか, まだ) e, ao aplicar a regra nova, esquece a outra na mesma frase. O vocabulário tem Anki; a gramática não tinha agenda: cada regra era ensinada uma vez e só voltava se desse erro. Decisões dele: (1) caderno de regras no painel; (2) revisão espaçada de regras no painel **e** num deck de gramática no Anki; (3) uma etapa de **explicação** do conteúdo novo antes dos exercícios (tipo `explicacao`, bloco `novo`); (4) lição de **25** exercícios. O esquema 4 refaz a tabela `exercicio` (CHECK novo e `regra_id`), pela mesma receita do esquema 3.
- **23/10** — Segunda tentativa com dica (§9.6) e agenda com deslize × lacuna (§13.2), recomendação do relatório de pesquisa aprovada por ele. Lyster & Saito (2010): dicas que fazem o aluno se corrigir (d = 0,83) superam mostrar a resposta certa (d = 0,53), sem perda no teste tardio, e treinam o automonitoramento. Separar **deslize** (corrigiu sozinho com a dica: sabe a regra, falhou sob carga) de **lacuna** (não corrigiu: não sabe) deixa uma regra madura que escorregou uma vez recuar um degrau em vez de voltar ao zero. Junto: o aviso da madrugada no `hoje()` (sono curto prejudica codificação e memória de trabalho) e a linha "avalie a REGRA" no cartão do deck de gramática. Esquema 5: só colunas novas (`ALTER TABLE ADD COLUMN`), sem refazer tabela.
- **17/10** — Fase 2 entregue: motor de exercícios, 4 ferramentas MCP, API como serviço `systemd --user` (`japones-painel`) e o painel. A primeira lição (revisão do dia 68, os 8 tipos) foi respondida numa CÓPIA do banco para testar o fluxo inteiro; o banco real ficou intacto.

## 9. Exercícios [CONTRATO]

### 9.1 Modelo

Uma **lição** (`licao`) é a lista de exercícios de um dia de estudo, criada pelo tutor via MCP. Cada **exercício** tem campos comuns e um `dados` próprio do tipo, **com o gabarito**, que nunca sai do servidor: o navegador recebe só o `render` (§9.2), já embaralhado.

Campos comuns de um exercício:

| Campo | Valor |
|---|---|
| `tipo` | `escolha` · `achar_erro` · `ligar` · `ordenar` · `completar` · `digitar` · `conjugar` · `ouvir` · `producao` · `explicacao` (não é exercício: ver abaixo) |
| `bloco` | `aquecimento` · `novo` (rótulo "Conteúdo novo", desde 23/10) · `verificacao` · `producao` · `revisao`; padrão `verificacao` (`novo` no `explicacao`) |
| `categoria` | categoria de erro (§4.2) que um erro neste exercício alimenta; opcional |
| `regra` | slug de uma regra do caderno (§13) que este exercício revisa; opcional. Grava `regra_id`; slug desconhecido recusa a lição. A primeira resposta certa/errada move a agenda da regra (§13.2) |
| `enunciado` | a instrução, em português (pode conter japonês); opcional só no `explicacao` |
| `explicacao` | a regra em uma ou duas linhas, mostrada depois da resposta (pedido dele em 16/10: toda correção reexplica a regra) |
| `dica_erro` | opcional (23/10): dica curta (1 a 200 caracteres) para a **segunda tentativa** depois de uma primeira resposta errada (§9.6). Recusada no `producao` e no `explicacao` |
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
| `ouvir` | ditado: `{"texto": "すしを食べたことがあります", "aceitas": [..]}`; compreensão: `{"texto": "...", "opcoes": [..], "correta": ".."}`. Opcionais: `fala` (o que a voz lê, padrão = `texto`; kana para kanji de leitura ambígua), `voz` (`F` padrão, ou `M`). O servidor acrescenta `audio` (§12.3) | `{"modo": "ditado" \| "escolha", "audio": "/api/audio/<nome>.mp3", "opcoes"?: [..]}` (nunca o texto) | ditado `{"texto": "...", "toques": 3}`; compreensão `{"opcao": "...", "toques": 3}` (`toques` = quantas vezes tocou, opcional, informativo) | ditado: como `digitar` (fora das `aceitas` → `revisar` com diff); compreensão: automática |
| `producao` | `{"minimo": 3, "dicas": [..]}` | igual | `{"frases": [..]}` | sempre `revisar`: o tutor corrige pelo MCP |
| `explicacao` | `{"md": "<markdown>"}` **ou** `{"regra": "<slug>"}` (o markdown vem de `regra.explicacao_md` na renderização; slug inexistente ou regra sem explicação recusa a lição) | `{"md": "...", "titulo": str \| null, "regra": slug \| null}` | **nenhum**: o painel mostra o texto e um botão "Entendi" que só avança; um POST de resposta devolve 400 | nenhuma |

**Normalização** antes de comparar texto: NFKC, sem espaços, sem `。、.,!?！？`. Katakana e hiragana **não** se equivalem (trocar é erro de `katakana`/`kana:troca`).

**Veredito:** `certo` · `errado` · `revisar`. Só a **primeira** resposta conta para placar e para a tabela `erro`; dá para responder de novo para praticar. Num exercício com `dica_erro`, a primeira resposta `errado` abre a segunda tentativa com dica (§9.6), que não muda o placar.

**Erro automático:** a primeira resposta `errado` de um exercício grava uma linha em `erro` (`categoria` do exercício ou `outro`; `escrito` = a resposta; `correto` = o gabarito; `porque` = a explicação; bloco `aquecimento`→`abertura`, `novo`→`verificacao`, `revisao`→`outro`). Um `revisar` corrigido como `errado` pelo tutor também grava.

**`explicacao` não é exercício** (23/10): fica fora do placar e das contagens (`resumo_licoes`, `resultado_licao`, acerto por tipo), da tabela `erro`, dos pesos e do sorteio do `planejar_tipos`, e do critério de lição concluída.

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

**Esquema 4** (23/10): a tabela `exercicio` é refeita (SQLite não altera CHECK) com `bloco` aceitando `novo`, `tipo` aceitando `explicacao` e a coluna `regra_id INTEGER REFERENCES regra(id) ON DELETE SET NULL`; e nasce a tabela `regra` (§13.1).

**Esquema 5** (23/10, §9.6 e §13.2): só colunas novas — o SQLite acrescenta coluna sem refazer a tabela. Roda numa transação com a troca do `user_version` (tudo ou nada).

```sql
ALTER TABLE exercicio ADD COLUMN dica_erro TEXT;
ALTER TABLE resposta  ADD COLUMN apos_dica INTEGER NOT NULL DEFAULT 0 CHECK (apos_dica IN (0, 1));
ALTER TABLE erro      ADD COLUMN exercicio_id INTEGER REFERENCES exercicio(id) ON DELETE SET NULL;
ALTER TABLE erro      ADD COLUMN deslize INTEGER NOT NULL DEFAULT 0 CHECK (deslize IN (0, 1));
ALTER TABLE regra     ADD COLUMN deslizes INTEGER NOT NULL DEFAULT 0;
ALTER TABLE regra     ADD COLUMN intervalo_dia REAL;
ALTER TABLE regra     ADD COLUMN lacunas_dia INTEGER NOT NULL DEFAULT 0;
```

A lição fica `concluida` quando todo exercício **que não é `explicacao`** tem a primeira resposta (uma dica pendente não segura a lição, §9.6).

### 9.4 Sorteio dos tipos (`planejar_tipos`)

"Sempre variando, mas utilizando todos." Peso de cada tipo = 1 + **2** se não apareceu nas últimas 2 lições + **2 × taxa de erro** do tipo nos últimos 30 dias. Com `n` ≥ número de tipos (o padrão da biblioteca, 9; o da ferramenta MCP, **25** desde 23/10/2026 — antes 20, desde 21/10, pedido dele: "mais questões sobre o conteúdo novo de cada dia"), cada tipo entra uma vez e o peso decide as vagas que sobram; com menos, o peso decide quem entra. O `explicacao` não entra no sorteio: o tutor o acrescenta à mão, antes dos exercícios do conteúdo novo. No máximo 2 exercícios do mesmo tipo por lição enquanto couber; acima de 17 o teto sobe só o necessário (3 com 20 e com 25); `producao` entra sempre, no fim (regra 4 do CLAUDE.md: produção ativa todo dia). O tutor recebe a sequência e escreve o conteúdo de cada exercício a partir da necessidade do dia (padrões abertos, erros recentes, conteúdo novo).

### 9.5 Ferramentas MCP novas

| Ferramenta | Faz |
|---|---|
| `planejar_tipos(n, semente)` | a sequência sorteada (§9.4) e o porquê de cada peso |
| `criar_licao(titulo, exercicios, data)` | valida cada exercício pelo tipo (e o `regra` de cada um contra o caderno, e o `dica_erro`), grava, devolve `id` e o link do painel |
| `resultado_licao(id)` | resumo da lição (padrão: a mais recente): veredito, resposta e gabarito de cada exercício, e os `revisar` pendentes; ignora o `explicacao`. Os exercícios que passaram pela dica trazem `autocorrigiu` (`true` deslize · `false` lacuna · `null` dica ainda pendente; sem a chave = não houve dica). A `contagem` traz `certo`, `errado`, `revisar`, `sem_resposta`, `deslizes` (errados corrigidos com a dica) e `lacunas` (`errado − deslizes`) |
| `corrigir_exercicio(exercicio_id, veredito, correcao)` | fecha um `revisar` (`certo`/`errado`) com a correção, que aparece no painel; se o exercício tem `regra`, move a agenda dela (só no primeiro fechamento) |

### 9.6 Segunda tentativa com dica (23/10/2026)

Recomendação do relatório de pesquisa, aprovada por ele (§8). Dica que faz o aluno se corrigir ensina mais que a resposta pronta, e o erro passa a ter dois tipos: **deslize** (corrigiu com a dica) e **lacuna** (não corrigiu).

- **Campo** `dica_erro` (§9.1): aponta *onde* olhar, sem dar a resposta. O tutor escreve com o checklist da aula: tempo do verbo · partícula de cada substantivo · forma do verbo pedida pela estrutura. Ex.: "Confira o tempo do verbo: a frase fala do passado." Validação: texto não vazio, até 200 caracteres, nunca no `producao` nem no `explicacao`; tudo ou nada como o resto. Fica fora do `render`: só aparece depois da primeira resposta errada.
- **Quando abre:** a **primeira** resposta sai `errado` pela correção **automática** e o exercício tem `dica_erro`. Vale para escolha, achar_erro, ligar, ordenar, completar, conjugar e ouvir (compreensão). No digitar e no ditado a correção automática só dá `certo` ou `revisar` (o `revisar` vai para o tutor, sem dica), então a dica deles só apareceria se esse veredito mudasse.
- **Dica pendente:** o POST da primeira resposta devolve `dica` com `gabarito` vazio, `explicacao` nula e `detalhe` vazio; a leitura da lição (`resultado`) também os esconde. O gabarito não sai do servidor antes da segunda tentativa.
- **Segunda tentativa:** o próximo POST de resposta do exercício **é** a segunda tentativa (quem decide é o servidor: primeira `errado` automática, exercício com dica e nenhuma linha `apos_dica`). Grava `resposta.apos_dica = 1` e devolve a correção completa com `autocorrigiu`. **Desistir** ("Ver a resposta") é `POST /api/exercicios/{id}/desistir`: grava a linha `apos_dica = 1` com `resposta = {"desistiu": true}` e veredito `errado`. Os POSTs seguintes são o "Praticar de novo", com `apos_dica = 0`, como antes.
- **Placar:** só a primeira resposta conta — o exercício fica `errado` no placar, nas contagens, no acerto por tipo e no `planejar_tipos`. `autocorrigiu`: `true` = 2ª certa (**deslize**); `false` = 2ª errada ou desistência (**lacuna**); `null` = sem dica ou dica pendente.
- **Tabela `erro`:** o erro da primeira resposta é gravado na hora, como sempre, agora com `exercicio_id`; a segunda tentativa certa liga `deslize = 1` nessa linha.
- **Agenda da regra** (§13.2): a lacuna é aplicada já na primeira resposta; a segunda certa a reclassifica como deslize (`regras.deslize`).
- **Dica abandonada** (fechou a aba, pulou de exercício e não voltou) fica como lacuna: a agenda já a tratou assim, e a lição conclui do mesmo jeito.

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
| `GET /api/licoes/{id}` | `{id, data, titulo, status, exercicios: [{id, ordem, bloco, tipo, categoria, enunciado, render, resultado}]}`; `resultado` é `null` ou `{veredito, resposta, gabarito, explicacao, detalhe, correcao, dica, segunda, autocorrigiu}` da primeira resposta. `dica`: o texto, quando a primeira saiu errada num exercício com `dica_erro` (senão `null`); `segunda`: `null`, `{resposta, veredito, detalhe}` (a 2ª tentativa) ou `{"desistiu": true}`; `autocorrigiu`: `true`/`false`/`null` (§9.6). Com a dica pendente (`dica` e `segunda: null`), `gabarito` vem `""`, `explicacao` `null` e `detalhe` `{}` |
| `POST /api/exercicios/{id}/resposta` | corpo `{"resposta": {...§9.2}, "tempo_ms": 1234}` → `{veredito, gabarito, explicacao, detalhe, contou}`. Primeira resposta errada com dica: `{veredito: "errado", gabarito: "", explicacao: null, detalhe: {}, contou: true, dica: "..."}`. Segunda tentativa: a correção dela, `contou: false` e `autocorrigiu`. 400 num `explicacao` (não tem resposta) |
| `POST /api/exercicios/{id}/desistir` | "Ver a resposta" com a dica pendente (§9.6) → `{veredito: "errado", gabarito, explicacao, detalhe (da 1ª), contou: false, autocorrigiu: false}`; 409 se não há dica esperando; 404 se o exercício não existe |
| `GET /api/regras` | o caderno (§13.6): `[{slug, titulo, categoria, ensinada_em, explicacao_md, intervalo, proxima, dias, acertos, erros, deslizes, ultima_revisao, ultima_falha, status}]`, por `proxima` |
| `GET /api/erros?dias=30&categoria=` | o mesmo de `erros()` do MCP |
| `GET /api/erros/painel?dias=90` | §12.1 |
| `GET /api/registro?busca=&limite=20` | o mesmo de `registro_antigo()` do MCP |
| `GET /api/anki/painel` | §12.2 |
| `GET /api/kotoba/buscar?q=&limite=20` | §12.4 |
| `GET /api/kotoba/kanji/{literal}` | a ficha do kanji (`kotoba.kanji`); 404 se não houver |
| `GET /api/kotoba/historico?dias=30` | §12.4 |
| `GET /api/kotoba/listas` | as listas do Kotoba (`kotoba.listas`) |
| `GET /api/audio/{nome}.mp3` | o mp3 de um exercício `ouvir` (§12.3) |
| `GET /` e rotas do SPA | `web/dist/index.html` (o build do React) |

`detalhe` por tipo: `ligar` → `{"pares": [{"esquerda", "escolhida", "certa", "ok"}]}`; `completar` → `{"lacunas": [true, false]}`; `ordenar` → `{"montada": "..."}`; `digitar`/`conjugar` → `{"diff": [{"op": "igual"|"faltou"|"sobrou", "texto": "..."}], "comparado_com": "..."}`; `achar_erro` → `{"errado": 0, "correcao": "..."}`.

`gabarito` é sempre um texto pronto para mostrar ("猫は部屋にいます"; "日本を → 日本に").

## 11. Painel (`web/`) [CONTRATO de telas]

React + Vite + TypeScript, Tailwind + shadcn/ui, TanStack Query, React Router, FullCalendar, react-markdown, dnd-kit. Claro/escuro pelo sistema. Fonte japonesa da máquina (`Noto Sans CJK JP`).

| Rota | Tela |
|---|---|
| `/` | **Hoje**: dia do plano, streak e recorde; plano de hoje e o que a última aula deixou; lembrete de abertura; botão **Aula de hoje** (se houver lição); pendências do Trello com link (vencidas em vermelho); checklists da semana; Anki (hoje/ontem, fila, retenção, em loop); padrões abertos |
| `/aula` e `/aula/:id` | **Aula**: um exercício por vez, barra de progresso, correção na hora com a explicação, resumo no fim. **Dica** (§9.6): primeira resposta errada num exercício com dica → em vez da correção, "Quase. Dica: …" com a resposta dele, o widget de novo em branco para a segunda tentativa e o botão **Ver a resposta** (desistir); depois, a correção de sempre com "Corrigiu com a dica" (deslize) ou "Errado — nem com a dica" / "você pediu a resposta". Na barra, a dica pendente tem ícone próprio; ao reabrir a lição, ela é a primeira pendente; o resumo conta os corrigidos com a dica. O item `explicacao` mostra o rótulo do bloco ("Conteúdo novo"), o markdown (o mesmo `Markdown` das correções: react-markdown com GFM, sem HTML cru) e um botão **Entendi** que só avança; a barra de progresso conta só os exercícios |
| `/regras` | **Regras** (o caderno, 23/10): as regras em três grupos — **Vencem hoje**, **Frágeis** (mais erros que acertos) e **Em dia** —, cada uma expansível com a explicação e os números (acertos, erros, deslizes, próxima revisão, intervalo, ensinada em) |
| `/calendario` | mês: cor do dia pelo tipo da aula (completa/parcial/sem mesa), plano, prazos do Trello, lições, ponto de áudio; clique abre o detalhe do dia |
| `/aulas` e `/aulas/:data` | histórico com busca; a entrada do diário renderizada |
| `/erros` | **Erros** (Fase 3): erros por semana empilhados por grupo de categoria; tabela de categorias (clicar filtra a lista); a lista (escrito → correto, porquê; o deslize leva a marca "corrigiu com a dica"); padrões abertos e resolvidos; acerto por tipo de exercício; busca no registro antigo |
| `/anki` | **Anki** (Fase 3): hoje/ontem, fila, retenção 30 d com o alerta; mapa de calor dos cartões por dia desde 03/08 com o áudio; retenção por semana (linha dos 85%); previsão de 14 dias; maturidade; botões; em loop, travam, bandeira; baralhos |
| `/kotoba` | **Kotoba** (Fase 3): busca (IME), verbete com leitura, JLPT, acento, glosas PT (EN recolhidas) e se já tem cartão; clicar num kanji abre a ficha; o histórico de consultas por dia de estudo; as candidatas a cartão; as listas |

**Exercício `ouvir`:** botão de tocar (conta os toques), velocidade normal ou devagar (`playbackRate` 0,75, que no navegador preserva o tom), o ditado digita com a mesma regra de IME abaixo.

**Entrada japonesa (IME):** ele digita com ibus-mozc. Enter durante a composição (`isComposing`) **nunca** envia nem avança.

## 12. Fase 3: Erros, Anki, Kotoba e o exercício de ouvir [CONTRATO]

Pedido dele em 17/10, depois da Fase 2 ("prossiga para a fase"). O que era ideia na entrega da Fase 2 (as telas com gráficos e um exercício de ouvir) virou o escopo.

### 12.1 `GET /api/erros/painel?dias=90`

```json
{"desde": "2026-07-19", "primeiro_erro": "2026-10-16", "total": 11,
 "por_categoria": [{"categoria": "particula:wo", "grupo": "particula", "n": 2, "ultimo": "2026-10-16"}],
 "por_semana": [{"semana": "2026-10-12", "grupo": "particula", "n": 5}],
 "por_bloco": {"abertura": 3, "producao": 8},
 "tipos_exercicio": [{"tipo": "conjugar", "respondidos": 4, "certos": 3, "errados": 1, "revisar": 0, "taxa_erro": 0.25}],
 "padroes": {"abertos": [{...padrao}], "resolvidos": [{...padrao}]}}
```

`primeiro_erro` = o dia do erro mais antigo do banco (o registro erro a erro começou em 16/10; antes disso, "nenhum erro" não quer dizer nada). `grupo` = o prefixo antes do `:` (`particula:wo` → `particula`; sem `:`, a própria categoria). `semana` = a segunda-feira da semana do dia de estudo. `tipos_exercicio` conta só a **primeira** resposta (a que conta), no mesmo período.

### 12.2 `GET /api/anki/painel`

```json
{"status": {...o mesmo de anki()} | {"erro": "..."},
 "graficos": {"retencao_semanal": [{"semana": "2026-10-12", "revisoes": 812, "acertos": 701, "pct": 86.3}],
              "maturidade": {"novos": 1035, "aprendendo": 0, "jovens": 347, "maduros": 1180, "suspensos": 0},
              "previsao": [{"data": "2026-10-17", "devidos": 140}]} | {"erro": "..."},
 "por_dia": [{"data": "2026-08-03", "cartoes": 40, "minutos": 12.5, "audio": 1}]}
```

- `retencao_semanal`: revisões de cartão já aprendido (`revlog.type = 1`) por semana de dia de estudo; acerto = qualquer botão menos *again*. As 12 últimas semanas.
- `maturidade`: jovem = revisão com intervalo < 21 dias; maduro = ≥ 21 (a régua do próprio Anki); suspensos e enterrados contam só em `suspensos`.
- `previsao`: revisões devidas nos próximos 14 dias de estudo; o dia de hoje inclui os atrasados.
- `por_dia`: desde 03/08, cartões e minutos do `revlog` ao vivo, e `audio` da tabela `trajeto` (1, 0 ou `null` = não informado). Com o Anki fora do ar, cai nos números gravados em `trajeto`.

### 12.3 Áudio do exercício `ouvir` (`japones/audio.py`)

- Voz neural do edge-tts, a mesma do diagnóstico mensal: `F` = Nanami, `M` = Keita, ritmo `-15%` (o N5 real é falado devagar).
- O mp3 é gravado **no `criar_licao`**, não na hora de tocar: a lição tem de funcionar se a rede cair depois. Mora em `~/.local/share/japones/audio/<nome>.mp3`, com `nome` = 20 hex do SHA-256 de `voz|ritmo|fala` (a mesma fala reaproveita o arquivo; o nome não revela o texto, que é a resposta).
- Sem rede, o `criar_licao` recusa a lição inteira (tudo ou nada, como a validação), dizendo qual exercício falhou: o tutor troca o `ouvir` por outro tipo.
- Fica fora do git e do backup: é regenerável a partir do `dados`.
- O tutor não ouve o que gera: o servidor confere só que o arquivo tem som (tamanho > 0).

### 12.4 Kotoba no painel

`GET /api/kotoba/buscar?q=` → `{"resultados": [ ...kotoba.buscar(q, detalhado=True), cada um com "tem_cartao": true | false | null ]}`.

`GET /api/kotoba/historico?dias=30` →

```json
{"dias": [{"data": "2026-10-16", "consultas": [{"tipo": "entry", "rotulo": "持つ · segurar", "palavra": "持つ",
                                                "consulta": null, "kanji": null, "quando": "2026-10-17T02:18:37",
                                                "tem_cartao": false}]}],
 "sem_cartao": [{"palavra": "持つ", "rotulo": "持つ · segurar", "vezes": 2, "ultima": "2026-10-16"}]}
```

- O dia é o **dia de estudo** (a consulta das 02:18 de 17/10 é do dia 16).
- `tem_cartao`: a palavra (ou a leitura, na busca) aparece como um **campo inteiro** de alguma nota do Anki, sem HTML. É uma pista, não uma verdade: o cartão de 食べる pode estar como たべます. `null` = o Anki não abriu.
- `sem_cartao`: as palavras abertas (`tipo = entry`) sem cartão, mais consultadas primeiro: as candidatas do Passo 4 da `/estudo`. O MCP `consultas_kotoba` devolve a mesma lista no campo `sem_cartao`.
- O link `kotoba://` **não** aparece no painel: no Linux o atalho do Kotoba não registra o esquema, e o link não abriria nada. O painel mostra o verbete inteiro.

## 13. Caderno de regras: revisão espaçada da gramática [CONTRATO]

Pedido dele em 23/10/2026 (ver §8). O vocabulário tem o Anki; a gramática passa a ter agenda própria, no painel e num deck de gramática no Anki.

### 13.1 Tabela `regra` (esquema 4)

```sql
CREATE TABLE regra (id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL, titulo TEXT NOT NULL,
  categoria TEXT,                -- a categoria de erro associada (§4.2), ex. 'gramatica:te-mo-ii'
  ensinada_em TEXT,              -- AAAA-MM-DD
  explicacao_md TEXT,
  intervalo REAL NOT NULL DEFAULT 0, proxima TEXT,        -- a agenda (§13.2)
  acertos INTEGER NOT NULL DEFAULT 0, erros INTEGER NOT NULL DEFAULT 0,
  ultima_revisao TEXT, ultima_falha TEXT,
  criada_em TEXT DEFAULT (datetime('now','localtime')),
  -- esquema 5 (§13.2): deslize × lacuna
  deslizes INTEGER NOT NULL DEFAULT 0,  -- erros corrigidos com a dica; desde então `erros` conta só lacunas
  intervalo_dia REAL,                   -- o intervalo antes do primeiro evento do dia `ultima_revisao`
  lacunas_dia INTEGER NOT NULL DEFAULT 0);  -- lacunas no dia `ultima_falha`
```

### 13.2 Agenda (`regras.agendar(con, regra_id, veredito, dia)`)

Repetição espaçada simples, por regra. `dia` = `dominio.dia_de_estudo()` (regra das 04:00). Chamada quando um exercício com `regra_id` recebe a **primeira** resposta com veredito automático `certo`/`errado`, e quando um `revisar` dele é fechado pelo tutor (`corrigir_exercicio`) como `certo`/`errado`.

- Primeiro evento da regra num dia novo (`ultima_revisao != dia`): guarda `intervalo_dia = intervalo` (o intervalo de antes do dia) e zera `lacunas_dia`.
- `errado` → `intervalo = 1`, `proxima = dia + 1`, `erros += 1`, `lacunas_dia += 1`, `ultima_falha = ultima_revisao = dia`. É a **lacuna**, e vale na hora mesmo com a dica pendente (§9.6).
- `certo` → `acertos += 1`. Se `ultima_falha == dia` ou `ultima_revisao == dia`, o intervalo **não cresce** (um erro no dia segura a regra para amanhã; vários acertos no mesmo dia contam uma vez só). Senão `intervalo = 2` se `intervalo < 2`, senão `min(60, round(intervalo × 2,5))`. `proxima = dia + intervalo`, `ultima_revisao = dia`.

Sequência resultante, só com acertos em dias diferentes: 2, 5, 12, 30, 60 dias. **Vencida** = `proxima <= dia de estudo`.

**Deslize** (23/10, `regras.deslize(con, regra_id, dia_da_falha)`): a segunda tentativa depois da dica saiu certa (§9.6). `dia_da_falha` = o dia de estudo da primeira resposta.

- `erros -= 1`, `deslizes += 1`: desde o esquema 5, `erros` conta só lacunas (e o status `fragil` = `erros > acertos` também).
- Se a agenda não andou depois daquele dia (`ultima_falha == ultima_revisao == dia_da_falha`): `lacunas_dia -= 1`, e se não sobrou lacuna no dia a regra **recua um degrau** em vez de zerar: `intervalo = max(1, round(intervalo_dia / 2,5))`, `proxima = dia_da_falha + intervalo`. Se sobrou outra lacuna no dia, ela segura a regra em 1. Se houve evento num dia posterior, só os contadores mudam.
- Exemplos: 12 → 5; 30 → 12; 60 → 24; 5 → 2; 2 → 1. `intervalo_dia` nulo (regra sem evento desde o esquema 5) usa o intervalo atual, que depois da lacuna é 1: na dúvida, o deslize vale como lacuna.

O pior resultado do dia vence: lacuna > deslize > acerto. Vários deslizes no mesmo dia recuam um degrau só (o recuo parte sempre de `intervalo_dia`), como vários acertos crescem uma vez só. E `ultima_falha` continua sendo o dia: um acerto depois do deslize, no mesmo dia, não faz o intervalo crescer.

**Por que a lacuna entra na primeira resposta, e não depois da dica:** a segunda tentativa pode nunca vir (aba fechada, pulou de exercício). Adiar a conta faria o erro sumir da agenda; aplicar na hora e reclassificar no deslize nunca perde um erro. O `intervalo_dia` e o `lacunas_dia` são o que o deslize precisa para refazer a conta.

### 13.3 Importador

`python -m japones.regras importar <arquivo.json> [--por-dia 5]` lê uma lista `[{"slug", "titulo", "categoria", "ensinada_em", "explicacao_md"}]` (só `slug` e `titulo` são obrigatórios; `{"regras": [...]}` também vale; campos a mais são ignorados) e faz upsert pelo `slug`. Tudo ou nada: um item inválido não grava nenhum. Campo ausente ou `null` não apaga o que já existe; a agenda de uma regra existente nunca é zerada. As regras sem agenda (`proxima` nula) recebem a primeira revisão espalhada: **5 por dia** a partir do dia de estudo atual (as 5 primeiras vencem hoje), na ordem de `ensinada_em` (as mais antigas primeiro; sem data, no fim). O conteúdo é do tutor (`plano/regras.json`).

### 13.4 Deck "Japonês::Gramática" no Anki

`tools/gerar_gramatica_apkg.py` espelha o `gerar_escrita_apkg.py`: lê `progresso/gramatica.tsv` (sentido em português | resposta em kana | nota | tags), gera `anki/gramatica.apkg` com cartão de digitar (`{{type:Resposta}}`, o Anki mostra o diff), modelo e deck com ids próprios e congelados, e importa pelo AnkiConnect (Anki fechado: só gera o arquivo). TSV sem linhas: não gera nem importa nada.

O verso do cartão diz (23/10): "Avalie a REGRA (tempo · partícula · forma do verbo), não a frase exata: frase válida de outro jeito = Good." O diff caractere por caractere marca como diferença uma frase válida escrita de outro jeito, e a nota tem de ser da regra. O modelo mudou antes da primeira importação; daqui para frente, ids e campos ficam como estão.

### 13.5 Ferramentas MCP (respostas enxutas)

| Ferramenta | Faz |
|---|---|
| `regras(vencidas=True, limite=10)` | `[{slug, titulo, ensinada_em, proxima, intervalo, acertos, erros}]` por `proxima`; `vencidas=True` = só `proxima <= dia de estudo` |
| `regra(slug)` | o registro completo, com `explicacao_md` |
| `salvar_regra(slug, titulo, categoria=None, explicacao_md=None, ensinada_em=None)` | upsert pelo `slug`; não zera a agenda de regra existente nem apaga campo passado como `null`; regra nova nasce com `intervalo 0` e `proxima = dia + 1` |

### 13.6 `GET /api/regras`

Lista de todas as regras, por `proxima` (sem agenda no fim). `status`: `vencida` se `proxima <= dia`; senão `fragil` se `erros > acertos` (`erros` = lacunas: o deslize não deixa a regra frágil); senão `em_dia`. `dias` = `proxima − dia de estudo` (≤ 0 = vencida; `null` sem agenda).
