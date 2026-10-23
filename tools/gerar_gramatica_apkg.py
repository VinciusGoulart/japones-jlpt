#!/usr/bin/env python3
"""
Gera anki/gramatica.apkg a partir de progresso/gramatica.tsv e importa via
AnkiConnect (fallback: so gera o arquivo).

DECK DE GRAMATICA ("Japonês::Gramática", 23/10/2026, pedido dele). Existe
porque o vocabulario tinha o Anki e a gramatica nao tinha agenda nenhuma: cada
regra era ensinada uma vez e so voltava se desse erro. O diagnostico do dia
foi que ele esquecia regras antigas (てもいいですか, まだ) e, ao aplicar a regra
nova, esquecia a outra na mesma frase. O painel tem o caderno de regras com
revisao espacada (sistema/DESIGN.md §13); este deck leva a mesma revisao para
o celular, no trajeto.

Mesmo formato do deck de escrita de precisao (gerar_escrita_apkg.py): o cartao
mostra o sentido em portugues, ele DIGITA a frase em japones, e o Anki mostra o
diff caractere por caractere ({{type:Resposta}}). Modelo e deck com ids
proprios e congelados, para nao colidir com os outros decks.

TSV: sentido em portugues | resposta em kana | nota (verso) | tags.
O conteudo e do tutor; TSV sem linhas nao gera nem importa nada.

Uso:  python3 tools/gerar_gramatica_apkg.py [--so-gerar]
"""
import hashlib
import json
import os
import sqlite3
import sys
import time
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import gerar_apkg as base
import gerar_vocab_apkg as vocab

# Relativos a raiz do repositorio, nao ao diretorio de onde se chama o script.
RAIZ = os.path.dirname(AQUI)
TSV = os.path.join(RAIZ, "progresso", "gramatica.tsv")
SAIDA = os.path.join(RAIZ, "anki", "gramatica.apkg")
DECK = "Japonês::Gramática"

# CONGELADO, como os demais. Nao mudar nunca: o Anki casa as notas pelo guid e
# recusa a reimportacao inteira se o tipo de nota mudar de id (ver gerar_apkg.id_estavel).
SEMENTE_GRAMATICA = "model::Japonês::Gramática::TypeIn"

CABECALHO = (
    "#separator:tab\n"
    "#colunas: sentido (frente) | resposta a digitar | nota (aparece no verso) | tags\n"
    "# Deck de GRAMATICA (Japonês::Gramática): uma linha por regra ensinada, escrita\n"
    "# pelo tutor. O cartao pede para digitar a frase e o Anki mostra o diff.\n"
)

CSS = (
    ".card { font-family: arial; font-size: 30px; text-align: center; "
    "color: black; background-color: white; }\n"
    "input#typeans { font-size: 30px; }\n"
    ".dica { font-size: 18px; color: #888; margin-top: 12px; }"
)


def guid_gramatica(sentido):
    return hashlib.sha1(("gramatica::" + sentido).encode("utf-8")).hexdigest()[:20]


def montar_modelo_typein(model_id, deck_id):
    return {
        str(model_id): {
            "id": model_id, "name": "Gramática (digite)", "type": 0,
            "mod": int(time.time()), "usn": -1, "sortf": 0, "did": deck_id,
            "tmpls": [
                {"name": "Digitar", "ord": 0,
                 # {{type:Resposta}} e o que abre a caixa de texto e gera o diff
                 "qfmt": "{{Sentido}}<br><br>{{type:Resposta}}",
                 "afmt": "{{FrontSide}}<hr id=answer>{{Resposta}}"
                         "<div class=dica>{{Nota}}</div>",
                 "did": None, "bqfmt": "", "bafmt": ""},
            ],
            "flds": [
                {"name": "Sentido", "ord": 0, "sticky": False, "rtl": False,
                 "font": "Arial", "size": 20, "media": []},
                {"name": "Resposta", "ord": 1, "sticky": False, "rtl": False,
                 "font": "Arial", "size": 20, "media": []},
                {"name": "Nota", "ord": 2, "sticky": False, "rtl": False,
                 "font": "Arial", "size": 20, "media": []},
            ],
            "css": CSS, "latexPre": "", "latexPost": "",
            "req": [[0, "any", [0]]],
            "tags": [], "vers": [],
        }
    }


def garantir_tsv():
    """Primeira execucao: cria o TSV so com o cabecalho (o conteudo e do tutor)."""
    if not os.path.exists(TSV):
        with open(TSV, "w", encoding="utf-8") as f:
            f.write(CABECALHO)


def ler_tsv():
    registros = []
    with open(TSV, encoding="utf-8") as f:
        for linha in f:
            linha = linha.rstrip("\n")
            if not linha or linha.startswith("#"):
                continue
            partes = linha.split("\t")
            if len(partes) < 2:
                continue
            sentido, resposta = partes[0], partes[1]
            nota = partes[2] if len(partes) > 2 else ""
            tags = partes[3] if len(partes) > 3 and partes[3].strip() else "gramatica"
            registros.append((sentido, resposta, nota, tags))
    return registros


def ids():
    deck_id = base.id_estavel("deck::" + DECK, 1600000000000)
    model_id = base.id_estavel(SEMENTE_GRAMATICA, 1700000000000)
    return deck_id, model_id


def gerar(registros):
    agora = int(time.time())
    agora_ms = agora * 1000
    deck_id, model_id = ids()

    tmp_db = SAIDA + ".tmp.anki2"
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
    con = sqlite3.connect(tmp_db)
    con.executescript(base.ESQUEMA)
    con.execute(
        "INSERT INTO col VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (1, agora, agora_ms, agora_ms, 11, 0, 0, 0,
         json.dumps(base.CONF_COL),
         json.dumps(montar_modelo_typein(model_id, deck_id)),
         json.dumps(base.montar_deck(deck_id, DECK)),
         json.dumps(base.CONF_DECK),
         json.dumps({})),
    )
    base_notas = agora_ms
    base_cartoes = agora_ms + 5_000_000
    for pos, (sentido, resposta, nota, tags) in enumerate(registros):
        nota_id = base_notas + pos
        campos = sentido + base.SEPARADOR + resposta + base.SEPARADOR + nota
        con.execute(
            "INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (nota_id, guid_gramatica(sentido), model_id, agora, -1,
             " " + tags.strip() + " ", campos, sentido,
             base.csum_do_campo(sentido), 0, ""),
        )
        con.execute(
            "INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (base_cartoes + pos, nota_id, deck_id, 0, agora, -1,
             0, 0, pos, 0, 0, 0, 0, 0, 0, 0, 0, ""),
        )
    con.commit()
    con.close()
    with zipfile.ZipFile(SAIDA, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tmp_db, "collection.anki2")
        z.writestr("media", "{}")
    os.remove(tmp_db)


def main():
    garantir_tsv()
    registros = ler_tsv()
    if not registros:
        # Sem linhas nao ha o que gerar: importar um pacote vazio so criaria um deck vazio no Anki dele.
        print(f"{os.path.relpath(TSV, RAIZ)}: nenhuma linha ainda — nada gerado nem importado")
        return
    gerar(registros)
    print(f"{os.path.relpath(SAIDA, RAIZ)}: {len(registros)} notas (digite a resposta)  ->  {DECK}")
    if "--so-gerar" not in sys.argv:
        try:
            vocab.ankiconnect("version")
        except Exception:
            print("  Anki do PC fechado — importe o arquivo manualmente (File > Importar)")
            return
        vocab.ankiconnect("importPackage", path=os.path.abspath(SAIDA))
        vocab.ankiconnect("sync")
        print("  importado direto no Anki do PC (AnkiConnect) + sync disparado")


if __name__ == "__main__":
    main()
