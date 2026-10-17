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
2. **Painel:** Hoje, Calendário, Aulas. API FastAPI sobre o mesmo núcleo; o build do React servido pelo FastAPI; serviço `systemd --user`.
3. **Erros, Anki, Kotoba** no painel.
4. **No repositório do Kotoba** (decisão dele): gravar o placar do "Treinar formas" num `drill_result` do `user.db`, para o painel mostrar a taxa de acerto por forma.

## 8. Registro de decisões

- **17/10** — `diario.md` continua existindo: é a narrativa, e é o que ele lê. O banco guarda a estrutura (placar, horário, erros) e uma cópia do texto para busca.
- **17/10** — `pontos_fracos` (123 entradas, 41 KB) não é reclassificado à força na migração: vai inteiro para `registro`, com a data, e os **erros categorizados começam a valer daqui para frente**. Os padrões abertos hoje são semeados à mão.
- **17/10** — SDK do MCP na versão 2 (`from mcp.server import MCPServer`); a 1.x chamava a classe de `FastMCP`.
