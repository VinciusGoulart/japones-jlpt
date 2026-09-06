#!/usr/bin/env python3
"""
Cria (ou atualiza) no Trello o cronograma da Fase 0: um card por semana.

E o dono UNICO da descricao dos cards. O anexar_decks_trello.py cuida so dos
arquivos .apkg. Rodar este script duas vezes nao duplica: se o card ja existe,
a descricao e atualizada no lugar.

Uso: python3 tools/criar_cronograma_trello.py <TRELLO_KEY> <TRELLO_TOKEN>
"""
import json
import sys
import urllib.parse
import urllib.request

BOARD_ID = "6a70b97141db00bba4d1da55"
API = "https://api.trello.com/1"

# Semanas de 7 dias: nao ha dia reservado so para revisao, porque a revisao
# acontece todo dia no trajeto pelo Anki.
SEMANAS = [
    {
        "nome": "Semana 1", "periodo": "03/08 a 09/08", "tema": "Hiragana, parte 1",
        "dias": [
            "Seg 03/08 - あ い う え お",
            "Ter 04/08 - か き く け こ",
            "Qua 05/08 - さ し す せ そ",
            "Qui 06/08 - た ち つ て と",
            "Sex 07/08 - な に ぬ ね の",
            "Sab 08/08 - は ひ ふ へ ほ",
            "Dom 09/08 - ま み む め も",
        ],
        "anki": [("kana-semana1-hiragana-parte1.apkg", 35),
                 ("kana-fase0-completo.apkg (opcional: os 150 de uma vez)", 150)],
        "marco": "Ler os 35 caracteres da semana em voz alta, sem travar.",
        "atencao": "Irregulares que quase todo iniciante erra: し = shi (nao 'si'), "
                   "ち = chi (nao 'ti'), つ = tsu (nao 'tu'), ふ = fu (som entre 'fu' e 'hu').",
    },
    {
        "nome": "Semana 2", "periodo": "10/08 a 16/08", "tema": "Fechar o hiragana",
        "dias": [
            "Seg 10/08 - や ゆ よ",
            "Ter 11/08 - ら り る れ ろ",
            "Qua 12/08 - わ を ん",
            "Qui 13/08 - が ぎ ぐ げ ご  +  ざ じ ず ぜ ぞ",
            "Sex 14/08 - だ ぢ づ で ど  +  ば び ぶ べ ぼ",
            "Sab 15/08 - ぱ ぴ ぷ ぺ ぽ",
            "Dom 16/08 - MARCO: escrever os 46 hiragana de memoria",
        ],
        "anki": [("kana-semana2-hiragana-parte2.apkg", 36)],
        "marco": "Escrever os 46 hiragana de memoria, sem consultar nada.",
        "atencao": "を e particula e soa 'o'. ん e a unica consoante sozinha. O dakuten (゛) e o "
                   "handakuten (゜) nao sao formas novas: sao marcas sobre letras que voce ja "
                   "conhece, por isso cabem duas series por dia.",
    },
    {
        "nome": "Semana 3", "periodo": "17/08 a 23/08", "tema": "Katakana, parte 1",
        "dias": [
            "Seg 17/08 - ア イ ウ エ オ",
            "Ter 18/08 - カ キ ク ケ コ",
            "Qua 19/08 - サ シ ス セ ソ",
            "Qui 20/08 - タ チ ツ テ ト",
            "Sex 21/08 - ナ ニ ヌ ネ ノ",
            "Sab 22/08 - ハ ヒ フ ヘ ホ",
            "Dom 23/08 - マ ミ ム メ モ",
        ],
        "anki": [("kana-semana3-katakana-parte1.apkg", 35)],
        "marco": "Ler katakana sem confundir os pares parecidos.",
        "atencao": "O katakana e MAIS dificil que o hiragana, nao menos: シ/ツ, ソ/ン, ク/ワ e ス/ヌ "
                   "sao quase identicos, e katakana aparece menos em texto comum. Os cartoes com a "
                   "tag 'confundivel' sao exatamente esses pares.",
    },
    {
        "nome": "Semana 4", "periodo": "24/08 a 30/08", "tema": "Fechar os silabarios",
        "dias": [
            "Seg 24/08 - ヤ ユ ヨ",
            "Ter 25/08 - ラ リ ル レ ロ",
            "Qua 26/08 - ワ ヲ ン",
            "Qui 27/08 - Yoon: きゃ しゃ ちゃ にゃ (com ゅ e ょ de cada)",
            "Sex 28/08 - Yoon: ひゃ みゃ りゃ (com ゅ e ょ de cada)",
            "Sab 29/08 - Yoon: ぎゃ じゃ びゃ ぴゃ (com ゅ e ょ de cada)",
            "Dom 30/08 - MARCO: os 92 de memoria + コーヒー パソコン テレビ",
        ],
        "anki": [("kana-semana4-katakana-parte2.apkg", 44)],
        "marco": "Escrever os 92 caracteres (hiragana + katakana) de memoria.",
        "atencao": "Os yoon seguem uma regra: consoante da base + や/ゆ/よ pequeno. Entendida a regra, "
                   "os 33 saem juntos. Cuidado so com os que perdem a vogal: しゃ = sha (nao 'shia'), "
                   "ちゃ = cha, じゃ = ja.  ///  ATENCAO: 30/08 e tambem o ULTIMO DIA de inscricao do "
                   "JLPT de dezembro/2026.",
    },
    {
        "nome": "Semana 5", "periodo": "31/08 a 06/09", "tema": "Primeiras estruturas - o romaji acaba aqui",
        "dias": [
            "A partir desta semana TUDO em kana. Romaji nunca mais.",
            "です / でした - afirmar e negar",
            "Particula は (topico) e が (sujeito)",
            "Particula を (objeto direto)",
            "Vocabulario: ~50 palavras, sempre dentro de frase",
            "Producao: 5 frases proprias por dia, corrigidas no /estudo",
        ],
        "anki": [("deck Japonês::Vocabulario (gerado pelas sessoes de mesa)", 0)],
        "marco": "Montar frases do tipo 'X e Y' sem consultar.",
        "atencao": "O romaji vira muleta e impede a leitura de virar automatica. Corte agora, doa o que doer.",
    },
    {
        "nome": "Semana 6", "periodo": "07/09 a 13/09", "tema": "Demonstrativos, numeros e tempo",
        "dias": [
            "これ / それ / あれ  e  この / その / あの",
            "Numeros e contagem",
            "Horas e datas",
            "Precos",
            "Particulas に (destino/tempo) e で (lugar da acao)",
        ],
        "anki": [("Japonês::Vocabulario + Kaishi 1.5k (15 novos/dia)", 0)],
        "marco": "Perguntar precos e dizer as horas.",
        "atencao": "Japones tem contadores diferentes por tipo de objeto. Aprenda os 2 ou 3 mais comuns "
                   "agora e deixe o resto para depois - tentar decorar todos trava o progresso.",
    },
    {
        "nome": "Semana 7", "periodo": "14/09 a 20/09", "tema": "Verbos na forma ます",
        "dias": [
            "Grupos de verbos",
            "Presente afirmativo e negativo (ます / ません)",
            "Passado (ました / ませんでした)",
            "Particulas と (e/com) e も (tambem)",
            "Vocabulario de rotina diaria",
        ],
        "anki": [("Japonês::Vocabulario + Kaishi 1.5k", 0)],
        "marco": "Descrever a propria rotina do dia por escrito.",
        "atencao": "ます e a forma formal. A forma casual so vem na Fase 1 - nao antecipe, "
                   "misturar os dois registros cedo demais gera confusao dificil de desfazer.",
    },
    {
        "nome": "Semana 8", "periodo": "21/09 a 27/09", "tema": "Adjetivos e primeiros kanji - fim da Fase 0",
        "dias": [
            "Adjetivos い e な",
            "Kanji de numeros: 一 二 三 四 五 六 七 八 九 十",
            "Kanji de dias: 日 月 火 水 木 金 土",
            "Kanji uteis: 人 本 年",
            "Revisao geral da Fase 0",
        ],
        "anki": [("Japonês::Vocabulario + Kaishi 1.5k + primeiros kanji", 0)],
        "marco": "FIM DA FASE 0: apresentar-se, descrever o dia e pedir algo num restaurante, por escrito.",
        "atencao": "Kanji sempre dentro de palavra, nunca solto. 日 sozinho quase nao ajuda; "
                   "日本 (Japao) ensina o kanji, a leitura e uma palavra usavel de uma vez.",
    },
]


def chamar(metodo, caminho, key, token, **params):
    params.update({"key": key, "token": token})
    if metodo == "GET":
        url = f"{API}{caminho}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(f"{API}{caminho}",
                                     data=urllib.parse.urlencode(params).encode(),
                                     method=metodo)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def descricao(s):
    linhas = [
        f"**Periodo:** {s['periodo']}  |  **Tema:** {s['tema']}",
        "",
        "### Mesa (1h/dia, rodando o /estudo)",
    ]
    linhas += [f"- {d}" for d in s["dias"]]
    linhas += ["", "### Trajeto (2h/dia, Anki no celular)"]
    for nome, qtd in s["anki"]:
        if qtd:
            linhas.append(f"- 📎 **Anexo neste card:** `{nome}` — {qtd} notas ({qtd*2} cartoes)")
        else:
            linhas.append(f"- {nome}")
    linhas += [
        "- Toque no anexo: o AnkiDroid abre e pergunta se quer importar. Reimportar nao duplica.",
        "- Configure **10 cartoes novos/dia** (cada caractere vira 2 cartoes: reconhecer e produzir).",
        "- Alem do Anki: 30 min de audio (Nihongo con Teppei for Beginners, do ep. 1).",
        "",
        "### Marco da semana",
        s["marco"],
        "",
        "### Atencao",
        s["atencao"],
    ]
    return "\n".join(linhas)


def main():
    if len(sys.argv) < 3:
        print("uso: python3 tools/criar_cronograma_trello.py <KEY> <TOKEN>")
        sys.exit(1)
    key, token = sys.argv[1], sys.argv[2]

    listas = {l["name"]: l["id"] for l in
              chamar("GET", f"/boards/{BOARD_ID}/lists", key, token, fields="name")}
    for nome in ["📚 Proximas semanas", "🔄 Semana atual", "✅ Concluido"]:
        if nome not in listas:
            listas[nome] = chamar("POST", "/lists", key, token,
                                  name=nome, idBoard=BOARD_ID, pos="bottom")["id"]
            print(f"lista criada: {nome}")

    cards = chamar("GET", f"/boards/{BOARD_ID}/cards", key, token, fields="name,desc")

    for i, s in enumerate(SEMANAS):
        titulo = f"{s['nome']} ({s['periodo']}) - {s['tema']}"
        desc = descricao(s)
        existente = next((c for c in cards if c["name"].startswith(s["nome"] + " (")), None)

        if existente:
            mudou = existente["desc"] != desc or existente["name"] != titulo
            if mudou:
                chamar("PUT", f"/cards/{existente['id']}", key, token, name=titulo, desc=desc)
                print(f"  atualizado: {titulo}")
            else:
                print(f"  sem mudanca: {titulo}")
        else:
            destino = listas["🔄 Semana atual"] if i == 0 else listas["📚 Proximas semanas"]
            chamar("POST", "/cards", key, token, name=titulo, desc=desc,
                   idList=destino, pos="bottom")
            print(f"  criado: {titulo}")


if __name__ == "__main__":
    main()
