# AGENTS.md — sistema de estudo

Instruções para agentes de código (Claude Code, Codex, Cursor…) que trabalham em `sistema/`.
O `CLAUDE.md` desta pasta só importa este arquivo, para as regras valerem nas duas famílias de ferramentas.

**Antes de mudar contrato (schema, ferramenta MCP, rota da API), leia e atualize `DESIGN.md`.** Ele é a fonte da verdade; o código segue o documento, não o contrário.

## O que é

Núcleo Python que junta Anki, Trello, Kotoba (dicionário próprio do estudante, em `../../dictionary`), `progresso/diario.md` e `plano/curriculo.md` num banco SQLite, e expõe tudo ao tutor (Claude Code) por um servidor MCP. O painel web (React) é a Fase 2.

## Comandos

```bash
# ambiente (o Python do sistema não tem ensurepip: o venv nasce sem pip e o pip vem do get-pip)
python3 -m venv --without-pip .venv
curl -sSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && .venv/bin/python /tmp/get-pip.py
.venv/bin/pip install -e ".[dev]"

.venv/bin/python -m pytest -q                  # testes (usam banco e diário temporários)
.venv/bin/python -m japones.migracao           # importa/reimporta o histórico (idempotente)
.venv/bin/python -m japones.mcp_server         # o servidor MCP (stdio) — o Claude Code sobe sozinho pelo ../.mcp.json
```

## Regras que não se quebram

1. **Dados pessoais fora do repositório.** O repositório é público no GitHub. O banco mora em `~/.local/share/japones/estudo.db`; `diario.md` e `estado.json` estão no `.gitignore`. Nunca commitar dado pessoal, nem em fixture de teste.
2. **Anki e Kotoba são só leitura, e de cópia.** Os bancos são dos apps. Um bug aqui não pode custar histórico de revisão nem o dicionário dele. O dicionário do Kotoba abre com `mode=ro&immutable=1`; o `user.db` e a coleção do Anki são copiados para um diretório temporário antes de abrir.
3. **Credenciais** só em `~/.config/japones/` (o Trello lê `trello.env` de lá). Nunca dentro da árvore.
4. **Nenhuma fonte derruba uma ferramenta MCP.** Fonte fora do ar vira `{"erro": "..."}` no campo dela; o resto da resposta segue. A aula não pode depender de rede.
5. **Respostas MCP enxutas.** Cada token volta a cada mensagem da aula; o limite de uso já estourou por excesso de contexto.
6. **Diário é append-only.** `registrar_aula` acrescenta; nada reescreve entradas antigas.
7. **Testes nunca tocam o banco real.** O `tests/conftest.py` aponta `JAPONES_DADOS`, `JAPONES_DB` e `JAPONES_DIARIO` para um diretório temporário antes de qualquer import.

## Estilo

- Português do Brasil em código, comentários, mensagens e commits (mensagem de commit em português, como o resto do repositório).
- Comentário explica o **porquê**, de preferência com a data e o incidente que gerou a regra (ver `tools/anki_status.py`).
- Datas são o **dia de estudo**: vira às 04:00 (`dominio.dia_de_estudo`). Nunca usar `date.today()` para decidir de que dia é uma aula.
- Biblioteca padrão primeiro. Dependência nova entra no `pyproject.toml` com o motivo ao lado.
