#!/usr/bin/env python3
"""
Gera anki/escrita-precisao.apkg a partir de progresso/escrita.tsv e importa
via AnkiConnect (fallback: so gera o arquivo).

DECK DE DIGITACAO DE PRECISAO ({{type:...}}): o cartao mostra o sentido em
portugues, ele DIGITA a palavra em japones, e o Anki exibe o diff caractere
por caractere. Existe porque os erros persistentes dele sao todos de UM
caractere — dakuten na silaba errada, sokuon, vogal longa, ん, ね/れ, し/ち —
exatamente o que o cartao de reconhecimento deixa passar e o diff denuncia.

Cada linha do TSV nasceu de um erro real documentado em pontos_fracos:
o deck e a lista de fantasmas dele, armada contra ele. Sessoes futuras
APPENDAM novos alvos no TSV quando um erro de execucao se repetir.

Recomendacao de uso: 5 novos/dia — digitar e lento, e o valor esta na
precisao, nao no volume.

Uso:  python3 tools/gerar_escrita_apkg.py [--so-gerar]
"""
import json
import os
import sqlite3
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_apkg as base
import gerar_vocab_apkg as vocab

TSV = "progresso/escrita.tsv"
SAIDA = "anki/escrita-precisao.apkg"
DECK = "Japonês::Escrita de precisão"

# CONGELADO, como os demais. Nao mudar nunca.
SEMENTE_ESCRITA = "model::Japonês::Escrita::TypeIn"

CSS = (
    ".card { font-family: arial; font-size: 30px; text-align: center; "
    "color: black; background-color: white; }\n"
    "input#typeans { font-size: 30px; }\n"
    ".dica { font-size: 18px; color: #888; margin-top: 12px; }"
)


def guid_escrita(sentido):
    import hashlib
    return hashlib.sha1(("escrita::" + sentido).encode("utf-8")).hexdigest()[:20]


def montar_modelo_typein(model_id, deck_id):
    return {
        str(model_id): {
            "id": model_id, "name": "Escrita de precisão (digite)", "type": 0,
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
            tags = partes[3] if len(partes) > 3 else "escrita"
            registros.append((sentido, resposta, nota, tags))
    return registros


def gerar(registros):
    agora = int(time.time())
    agora_ms = agora * 1000
    deck_id = base.id_estavel("deck::" + DECK, 1600000000000)
    model_id = base.id_estavel(SEMENTE_ESCRITA, 1700000000000)

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
            (nota_id, guid_escrita(sentido), model_id, agora, -1,
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
    registros = ler_tsv()
    gerar(registros)
    print(f"{SAIDA}: {len(registros)} notas (digite a resposta)  ->  {DECK}")
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
