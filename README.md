# 日本語 — Sistema de estudo de japonês com Claude Code

Do **zero absoluto ao JLPT N3**, com o [Claude Code](https://claude.com/claude-code) como tutor e gestor de rotina. Este repositório é o sistema completo: currículo, ferramentas, skills e automações — em uso real desde 03/08/2026.

## Como funciona

O estudo tem **duas frentes**, que falham por motivos diferentes e por isso são medidas separadamente:

- **Mesa (1h/dia)** — a sessão conduzida pelo Claude no terminal (`/estudo`): gramática nova, produção ativa de frases, correção com o porquê, e geração automática dos cartões de Anki do dia.
- **Trajeto (~2h/dia)** — Anki e áudio no celular, sem o Claude. É o que transforma a aula em memória de longo prazo.

O ciclo se fecha sozinho: a mesa gera vocabulário → um `.apkg` é importado no Anki do PC via AnkiConnect → o AnkiWeb sincroniza com o celular → o tutor lê a coleção real no dia seguinte e ajusta a rota com números, não com impressão.

## O que tem aqui

```
CLAUDE.md            — o contrato do tutor: papel, regras de conduta, perfil do estudante
plano/
  curriculo.md       — a sequência de conteúdo, dia a dia (o real, não o idealizado)
  roadmap.md         — fases e calendário JLPT
  metodo.md          — como estudar: estrutura da sessão, ferramentas, regras
progresso/
  vocabulario.tsv    — todo o vocabulário das sessões (fonte dos decks)
  estado.exemplo.json— esqueleto do estado, para começar o seu
.claude/skills/
  estudo/            — /estudo: a sessão diária de 1h
  progresso/         — /progresso: relatório e correção de rota
tools/
  gerar_vocab_apkg.py— tsv → .apkg → importação automática (AnkiConnect) → sync
  anki_status.py     — lê a coleção real do Anki (fila, retenção, minutos/dia)
  trello.py          — ponte com o board de acompanhamento (checklists, pendências)
anki/                — decks de kana prontos (.apkg) e geradores
```

O diário de sessões e o estado pessoal ficam fora do repositório (ver `.gitignore`) — o método é público, a vida não.

## Quer montar o seu?

Leia **[COMECE-O-SEU.md](COMECE-O-SEU.md)** — o passo a passo para clonar o sistema, zerar o estado e começar do seu próprio zero.

## Princípios que fazem o sistema funcionar

1. **Nunca inventar japonês** — dúvida honesta custa menos que erro fossilizado.
2. **60 minutos e acabou** — o que sustenta a meta é voltar amanhã.
3. **Repetição espaçada acima de tudo** — revisão atrasada vira sessão só de revisão.
4. **Produção ativa todo dia** — reconhecer não é saber.
5. **Registrar sempre** — sessão sem registro é sessão perdida para o planejamento.
6. **Texto na conversa não se cobra; card com data se cobra** — todo pedido operacional vira card com vencimento no Trello.
7. **Medir com dados, não com impressão** — o tutor lê a coleção do Anki, não o relato.
