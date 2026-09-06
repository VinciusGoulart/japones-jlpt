# Comece o seu — do zero ao seu próprio sistema

Este guia monta uma cópia limpa do sistema para **você**, com o seu perfil, o seu board e o seu Anki. Tempo estimado: ~40 minutos, uma vez só.

## 0. Pré-requisitos

- [Claude Code](https://claude.com/claude-code) instalado e funcionando no terminal
- Python 3 (já vem no Linux/macOS)
- Conta gratuita no [Trello](https://trello.com) e no [AnkiWeb](https://ankiweb.net)
- [Anki desktop](https://apps.ankiweb.net) no PC e AnkiDroid/AnkiMobile no celular

## 1. Clone e limpe

```bash
git clone https://github.com/VinciusGoulart/japones-jlpt.git meu-japones
cd meu-japones
cp progresso/estado.exemplo.json progresso/estado.json
echo "# Diário de sessões" > progresso/diario.md
```

O `.gitignore` já mantém `diario.md` e `estado.json` fora do git — seu progresso é seu.

Se você também parte do zero absoluto, **zere o vocabulário** (o arquivo vem com o vocabulário do dono original; as primeiras linhas `#` são o cabeçalho e ficam):

```bash
head -5 progresso/vocabulario.tsv > /tmp/vocab && mv /tmp/vocab progresso/vocabulario.tsv
```

## 2. Adapte o contrato do tutor

Abra o `CLAUDE.md` e reescreva a seção **Perfil do Estudante** com a SUA realidade: nome, cidade, nível inicial, quanto tempo você tem por dia (mesa e trajeto), e a meta com data. **Seja honesto no orçamento de horas** — o plano inteiro deriva daí, e meta que não fecha na conta vira frustração com data marcada.

Depois peça ao Claude, na primeira conversa: *"leia o CLAUDE.md e o plano/, e recalibre o roadmap para o meu perfil"*.

## 3. Trello (o cobrador)

1. Crie um board com as listas: `🔄 Semana atual`, `🎧 Audio (30 min/dia)`, `⚡ Pendencias`, `📅 Avisos do JLPT`, `Concluído`.
2. Pegue key e token em https://trello.com/app-key
3. Credenciais **fora do repositório** (ele pode virar público um dia):

```bash
mkdir -p ~/.config/japones
printf 'TRELLO_KEY=SUA_KEY\nTRELLO_TOKEN=SEU_TOKEN\n' > ~/.config/japones/trello.env
chmod 600 ~/.config/japones/trello.env
```

4. Troque o `BOARD_ID` no topo de `tools/trello.py` pelo id do seu board (está na URL dele) e rode `python3 tools/trello.py setup`.

## 4. Anki (o motor da memória)

1. No PC: instale o Anki, entre na sua conta AnkiWeb.
2. No celular: AnkiDroid/AnkiMobile, mesma conta, sincronização automática ligada.
3. **Kanji legível**: `sudo apt install fonts-noto-cjk` (sem isso, dakuten vira cisco e você "erra" o que não enxerga).
4. Add-on **AnkiConnect** (código `2055492159`, Tools → Add-ons → Get Add-ons) — é o que deixa o tutor importar os cartões do dia sozinho.
5. Baixe o deck de vocabulário [Kaishi 1.5k](https://github.com/donkuri/kaishi) e configure **10 cartões novos/dia** (não mais — 20/dia no começo é o erro que mais faz abandonar o Anki no terceiro mês).
6. Os decks de kana desta pasta (`anki/*.apkg`) são seus: importe o da semana 1 e comece.

## 5. A primeira sessão

```bash
claude
> /estudo
```

O tutor lê o estado (zerado), vê que é o dia 1, e começa do あ. A partir daí é rotina: 1h de mesa por dia, Anki e áudio no resto. O sistema cuida do resto — cartões, cobranças, correção de rota.

## As três regras que não se negociam

1. **Consistência vale mais que intensidade.** 1h todo dia ganha de 7h no domingo.
2. **O Anki decide o que revisar, não você.** Confie no algoritmo e use o botão Again sem culpa — ele é informação, não derrota.
3. **Produza todo dia.** Frase sua, errada e corrigida, vale mais que dez reconhecidas.

頑張ってください！
