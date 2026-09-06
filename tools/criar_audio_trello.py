#!/usr/bin/env python3
"""
Cria no Trello a lista de acompanhamento do AUDIO: um card por semana, cada um
com um checklist de 7 dias.

Por que existe: o audio e o terceiro bloco do trajeto (60 min de revisao + 30 de
cartoes novos + 30 de audio) e foi o unico que nunca aconteceu nos primeiros 8
dias. Ele estava enterrado numa linha da descricao dos cards de semana, e linha
de descricao nao se cobra. Checklist se cobra.

Por que os dias perdidos NAO entram: audio nao e divida. Ouvir 4h num sabado para
"recuperar" oito dias nao produz nada — a exposicao funciona por regularidade,
nao por volume acumulado. Os dias 1-8 ficam registrados na descricao como
historico e o checklist comeca do dia seguinte.

Rodar duas vezes nao duplica: lista, cards e checklists sao procurados por nome
antes de serem criados.

Uso: python3 tools/criar_audio_trello.py <TRELLO_KEY> <TRELLO_TOKEN>
"""
import json
import sys
import urllib.parse
import urllib.request

BOARD_ID = "6a70b97141db00bba4d1da55"
API = "https://api.trello.com/1"
LISTA = "🎧 Audio (30 min/dia)"

CANAL = "https://www.youtube.com/@nihongoconteppei"
PLAYLIST = "https://www.youtube.com/playlist?list=PLbsmSVzhiwvA8VNMAW_cuDqujRQULBjFd"
SPOTIFY = "https://open.spotify.com/show/4W4jYoKRmjlURKO1fIfcOK"
SITE = "https://nihongoconteppei.com/"

# A Semana 1 nao entra: ja passou inteira sem audio.
SEMANAS = [
    ("Semana 2", "10/08 a 16/08", ["Seg 10/08", "Ter 11/08", "Qua 12/08", "Qui 13/08",
                                   "Sex 14/08", "Sab 15/08", "Dom 16/08"]),
    ("Semana 3", "17/08 a 23/08", ["Seg 17/08", "Ter 18/08", "Qua 19/08", "Qui 20/08",
                                   "Sex 21/08", "Sab 22/08", "Dom 23/08"]),
    ("Semana 4", "24/08 a 30/08", ["Seg 24/08", "Ter 25/08", "Qua 26/08", "Qui 27/08",
                                   "Sex 28/08", "Sab 29/08", "Dom 30/08"]),
    ("Semana 5", "31/08 a 06/09", ["Seg 31/08", "Ter 01/09", "Qua 02/09", "Qui 03/09",
                                   "Sex 04/09", "Sab 05/09", "Dom 06/09"]),
    ("Semana 6", "07/09 a 13/09", ["Seg 07/09", "Ter 08/09", "Qua 09/09", "Qui 10/09",
                                   "Sex 11/09", "Sab 12/09", "Dom 13/09"]),
    ("Semana 7", "14/09 a 20/09", ["Seg 14/09", "Ter 15/09", "Qua 16/09", "Qui 17/09",
                                   "Sex 18/09", "Sab 19/09", "Dom 20/09"]),
    ("Semana 8", "21/09 a 27/09", ["Seg 21/09", "Ter 22/09", "Qua 23/09", "Qui 24/09",
                                   "Sex 25/09", "Sab 26/09", "Dom 27/09"]),
]

AVISO_INICIAL = (
    "> ⚠️ **Dias 1 a 8 (03/08 a 10/08) foram sem audio.** Fica como historico, nao "
    "como pendencia: audio nao e divida que se paga dobrando depois. Comeca daqui.\n\n"
)


def chamar(metodo, caminho, key, token, **params):
    params.update({"key": key, "token": token})
    if metodo == "GET":
        req = urllib.request.Request(f"{API}{caminho}?{urllib.parse.urlencode(params)}")
    else:
        req = urllib.request.Request(f"{API}{caminho}",
                                     data=urllib.parse.urlencode(params).encode(),
                                     method=metodo)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def descricao(periodo, primeira):
    linhas = []
    if primeira:
        linhas.append(AVISO_INICIAL)
    linhas += [
        f"**Periodo:** {periodo}  |  **30 min/dia**, todos os dias.",
        "",
        "### Onde ouvir — *Nihongo con Teppei for Beginners*",
        f"- ▶️ [Canal no YouTube]({CANAL})",
        f"- 🎬 [Playlist do podcast]({PLAYLIST})",
        f"- 🎧 [Spotify]({SPOTIFY})  |  🌐 [Site oficial]({SITE})",
        "",
        "### Como ouvir",
        "- **Sem legenda, sem pausar, sem procurar palavra.** Deixe rolar.",
        "- Episodios sao de 3 a 5 min: 30 minutos dao 6 a 8 episodios.",
        "- Nao precisa comecar do #1 — cada episodio e uma conversa avulsa, nao ha ordem.",
        "- Nao entender e o esperado nos primeiros meses. O ouvido esta aprendendo onde "
        "uma palavra termina e a outra comeca, coisa que o japones falado nao sinaliza.",
        "- Sab e dom nao tem trajeto: encaixe onde der (cozinhando, caminhando, academia).",
        "",
        "### Por que isso nao e opcional",
        "O JLPT tem **nota minima por secao**: no N3 sao 19/60 em cada uma das tres "
        "(vocabulario/gramatica, leitura e audicao), alem do total de 95/180. "
        "**Da para gabaritar gramatica e leitura e reprovar pela audicao** — as outras "
        "secoes nao compensam. E audicao nao melhora estudando mais gramatica: so com "
        "exposicao, em volume, ao longo de meses.",
    ]
    return "\n".join(linhas)


def main():
    if len(sys.argv) < 3:
        print("uso: python3 tools/criar_audio_trello.py <KEY> <TOKEN>")
        sys.exit(1)
    key, token = sys.argv[1], sys.argv[2]

    listas = {l["name"]: l["id"] for l in
              chamar("GET", f"/boards/{BOARD_ID}/lists", key, token, fields="name")}
    if LISTA in listas:
        id_lista = listas[LISTA]
        print(f"lista ja existe: {LISTA}")
    else:
        id_lista = chamar("POST", "/lists", key, token,
                          name=LISTA, idBoard=BOARD_ID, pos="bottom")["id"]
        print(f"lista criada: {LISTA}")

    existentes = {c["name"]: c for c in
                  chamar("GET", f"/lists/{id_lista}/cards", key, token, fields="name")}

    for i, (nome, periodo, dias) in enumerate(SEMANAS):
        titulo = f"🎧 {nome} ({periodo}) — audio 30 min/dia"
        desc = descricao(periodo, primeira=(i == 0))

        if titulo in existentes:
            card = existentes[titulo]
            chamar("PUT", f"/cards/{card['id']}", key, token, desc=desc)
            print(f"  atualizado: {titulo}")
        else:
            card = chamar("POST", "/cards", key, token,
                          name=titulo, desc=desc, idList=id_lista, pos="bottom")
            print(f"  criado: {titulo}")

        # checklist: so cria se ainda nao houver, para nao zerar o que ja foi marcado
        checklists = chamar("GET", f"/cards/{card['id']}/checklists", key, token,
                            fields="name")
        if any(c["name"] == "30 minutos" for c in checklists):
            print(f"     checklist ja existe, preservado")
            continue

        cl = chamar("POST", "/checklists", key, token,
                    idCard=card["id"], name="30 minutos")
        for dia in dias:
            chamar("POST", f"/checklists/{cl['id']}/checkItems", key, token,
                   name=dia, pos="bottom")
        print(f"     checklist criado com {len(dias)} dias")

    print("\nPronto. O checklist so e criado uma vez: rodar de novo preserva os checks.")


if __name__ == "__main__":
    main()
