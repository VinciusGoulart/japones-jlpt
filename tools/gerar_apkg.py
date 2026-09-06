#!/usr/bin/env python3
"""
Gera arquivos .apkg (formato nativo do Anki) sem dependencia externa.

O genanki nao instala neste sistema (venv exige sudo, pip bloqueado por PEP 668),
mas um .apkg e apenas um ZIP contendo:
  - collection.anki2  -> banco SQLite no schema 11 do Anki
  - media             -> JSON com o mapa de midias (vazio aqui: '{}')

Este modulo monta esse banco na mao. Schema 11 e o formato legado que todas as
versoes modernas do Anki e do AnkiDroid ainda importam.

O guid de cada nota e DETERMINISTICO (derivado do conteudo), entao reimportar o
mesmo cartao atualiza em vez de duplicar. Isso permite importar tanto o arquivo
da semana quanto o deck completo sem criar duplicatas.

Uso:  python3 tools/gerar_apkg.py
Saida: anki/*.apkg
"""
import hashlib
import json
import os
import sqlite3
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_kana_tsv as fonte

SEPARADOR = "\x1f"  # separador de campos do Anki

ESQUEMA = """
CREATE TABLE col (
    id integer primary key, crt integer not null, mod integer not null,
    scm integer not null, ver integer not null, dty integer not null,
    usn integer not null, ls integer not null, conf text not null,
    models text not null, decks text not null, dconf text not null, tags text not null
);
CREATE TABLE notes (
    id integer primary key, guid text not null, mid integer not null,
    mod integer not null, usn integer not null, tags text not null,
    flds text not null, sfld integer not null, csum integer not null,
    flags integer not null, data text not null
);
CREATE TABLE cards (
    id integer primary key, nid integer not null, did integer not null,
    ord integer not null, mod integer not null, usn integer not null,
    type integer not null, queue integer not null, due integer not null,
    ivl integer not null, factor integer not null, reps integer not null,
    lapses integer not null, left integer not null, odue integer not null,
    odid integer not null, flags integer not null, data text not null
);
CREATE TABLE graves (usn integer not null, oid integer not null, type integer not null);
CREATE TABLE revlog (
    id integer primary key, cid integer not null, usn integer not null,
    ease integer not null, ivl integer not null, lastIvl integer not null,
    factor integer not null, time integer not null, type integer not null
);
CREATE INDEX ix_notes_usn on notes (usn);
CREATE INDEX ix_cards_usn on cards (usn);
CREATE INDEX ix_cards_nid on cards (nid);
CREATE INDEX ix_cards_sched on cards (did, queue, due);
CREATE INDEX ix_revlog_cid on revlog (cid);
CREATE INDEX ix_revlog_usn on revlog (usn);
CREATE INDEX ix_notes_csum on notes (csum);
"""

CSS = (
    ".card { font-family: arial; font-size: 48px; text-align: center; "
    "color: black; background-color: white; }"
)

CONF_COL = {
    "nextPos": 1, "estTimes": True, "activeDecks": [1], "sortType": "noteFld",
    "timeLim": 0, "sortBackwards": False, "addToCur": True, "curDeck": 1,
    "newBury": True, "newSpread": 0, "dueCounts": True, "curModel": None,
    "collapseTime": 1200,
}

CONF_DECK = {
    "1": {
        "id": 1, "name": "Default", "mod": 0, "usn": 0, "maxTaken": 60,
        "autoplay": True, "timer": 0, "replayq": True,
        "new": {"bury": True, "delays": [1, 10], "initialFactor": 2500,
                "ints": [1, 4, 7], "order": 1, "perDay": 20,
                "separate": True},
        "rev": {"bury": True, "ease4": 1.3, "fuzz": 0.05, "ivlFct": 1,
                "maxIvl": 36500, "minSpace": 1, "perDay": 200},
        "lapse": {"delays": [10], "leechAction": 0, "leechFails": 8,
                  "minInt": 1, "mult": 0},
        "dyn": False,
    }
}


def csum_do_campo(texto):
    return int(hashlib.sha1(texto.encode("utf-8")).hexdigest()[:8], 16)


def guid_de(texto):
    """Deterministico: reimportar atualiza a nota em vez de duplicar."""
    return hashlib.sha1(("kana::" + texto).encode("utf-8")).hexdigest()[:20]


def id_estavel(texto, base):
    """ID deterministico entre execucoes.

    NAO usar hash() aqui: o hash de strings no Python e aleatorizado por processo
    (PYTHONHASHSEED), entao cada execucao geraria um ID diferente. Quando isso
    acontece com o ID do MODELO, o Anki recusa a reimportacao inteira -- ele casa
    as notas pelo guid, ve que o tipo de nota mudou, e aborta.
    """
    digest = hashlib.sha1(texto.encode("utf-8")).hexdigest()[:12]
    return base + int(digest, 16) % 10**9


def montar_modelo(model_id, deck_id, nome):
    """Modelo de 2 cartoes: reconhecer (kana->leitura) e produzir (leitura->kana)."""
    return {
        str(model_id): {
            "id": model_id, "name": nome, "type": 0, "mod": int(time.time()),
            "usn": -1, "sortf": 0, "did": deck_id,
            "tmpls": [
                {"name": "Reconhecer", "ord": 0,
                 "qfmt": "{{Front}}",
                 "afmt": "{{FrontSide}}<hr id=answer>{{Back}}",
                 "did": None, "bqfmt": "", "bafmt": ""},
                {"name": "Produzir", "ord": 1,
                 "qfmt": "{{Back}}",
                 "afmt": "{{FrontSide}}<hr id=answer>{{Front}}",
                 "did": None, "bqfmt": "", "bafmt": ""},
            ],
            "flds": [
                {"name": "Front", "ord": 0, "sticky": False, "rtl": False,
                 "font": "Arial", "size": 20, "media": []},
                {"name": "Back", "ord": 1, "sticky": False, "rtl": False,
                 "font": "Arial", "size": 20, "media": []},
            ],
            "css": CSS, "latexPre": "", "latexPost": "",
            "req": [[0, "any", [0]], [1, "any", [1]]],
            "tags": [], "vers": [],
        }
    }


def montar_deck(deck_id, nome):
    return {
        "1": {"id": 1, "name": "Default", "mod": 0, "usn": 0, "lrnToday": [0, 0],
              "revToday": [0, 0], "newToday": [0, 0], "timeToday": [0, 0],
              "collapsed": True, "browserCollapsed": True, "desc": "", "dyn": 0,
              "conf": 1, "extendNew": 10, "extendRev": 50},
        str(deck_id): {"id": deck_id, "name": nome, "mod": int(time.time()), "usn": -1,
                       "lrnToday": [0, 0], "revToday": [0, 0], "newToday": [0, 0],
                       "timeToday": [0, 0], "collapsed": False, "browserCollapsed": False,
                       "desc": "", "dyn": 0, "conf": 1, "extendNew": 10, "extendRev": 50},
    }


# CONGELADO. Nao mudar nunca, nem que o baralho seja renomeado.
#
# O model_id vinha de id_estavel("model::" + nome_deck), o que amarrava o tipo de
# nota ao NOME DO BARALHO. Renomear o deck (por exemplo, para criar subdecks de
# hiragana e katakana) mudaria o model_id, e o Anki recusa a importacao inteira
# quando as notas ja existem com outro tipo -- foi a falha do primeiro dia.
# Esta string preserva o valor que os decks ja importados carregam.
SEMENTE_MODELO = "model::Japonês::Fase 0 - Kana"


def gerar_apkg(registros, nome_deck, caminho_saida):
    """registros: lista de (frente, verso, tags)."""
    agora = int(time.time())
    agora_ms = agora * 1000
    # deck_id acompanha o nome (baralhos diferentes devem ter ids diferentes);
    # model_id NAO acompanha, pelo motivo explicado em SEMENTE_MODELO.
    deck_id = id_estavel("deck::" + nome_deck, 1600000000000)
    model_id = id_estavel(SEMENTE_MODELO, 1700000000000)

    tmp_db = caminho_saida + ".tmp.anki2"
    if os.path.exists(tmp_db):
        os.remove(tmp_db)

    con = sqlite3.connect(tmp_db)
    con.executescript(ESQUEMA)

    con.execute(
        "INSERT INTO col VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (1, agora, agora_ms, agora_ms, 11, 0, 0, 0,
         json.dumps(CONF_COL),
         json.dumps(montar_modelo(model_id, deck_id, "Kana (reconhecer e produzir)")),
         json.dumps(montar_deck(deck_id, nome_deck)),
         json.dumps(CONF_DECK),
         json.dumps({})),
    )

    # Espacos de ID separados para notas e cartoes: antes o id do 2o cartao de uma
    # nota colidia com o id da nota seguinte.
    base_notas = agora_ms
    base_cartoes = agora_ms + 5_000_000

    for posicao, (frente, verso, tags) in enumerate(registros):
        nota_id = base_notas + posicao
        campos = frente + SEPARADOR + verso
        con.execute(
            "INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (nota_id, guid_de(frente), model_id, agora, -1,
             " " + tags.strip() + " ", campos, frente, csum_do_campo(frente), 0, ""),
        )
        # dois cartoes por nota: ord 0 (reconhecer) e ord 1 (produzir)
        for ord_ in (0, 1):
            con.execute(
                "INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (base_cartoes + posicao * 2 + ord_, nota_id, deck_id, ord_, agora, -1,
                 0, 0, posicao, 0, 0, 0, 0, 0, 0, 0, 0, ""),
            )

    con.commit()
    con.close()

    with zipfile.ZipFile(caminho_saida, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tmp_db, "collection.anki2")
        z.writestr("media", "{}")
    os.remove(tmp_db)

    return len(registros)


# Subdecks por sistema de escrita, para poder estudar hiragana e katakana
# separadamente. Os yoon sao HIRAGANA, entao a semana 4 sai em dois arquivos:
# os 11 katakana que faltam vao para um deck, os 33 yoon para o outro.
DECK_HIRA = "Japonês::Fase 0 - Kana::Hiragana"
DECK_KATA = "Japonês::Fase 0 - Kana::Katakana"
DECK_PAI = "Japonês::Fase 0 - Kana"

# Mesma divisao de plano/curriculo.md (semanas de 7 dias, sem dia ocioso)
# 35 + 36 + 35 + 11 + 33 = 150 notas
SEMANAS = [
    ("kana-semana1-hiragana-parte1", DECK_HIRA, ["a", "ka", "sa", "ta", "na", "ha", "ma"], [], False, False),
    ("kana-semana2-hiragana-parte2", DECK_HIRA, ["ya", "ra", "wa"], [], True, False),
    ("kana-semana3-katakana-parte1", DECK_KATA, [], ["a", "ka", "sa", "ta", "na", "ha", "ma"], False, False),
    ("kana-semana4-katakana-parte2", DECK_KATA, [], ["ya", "ra", "wa"], False, False),
    ("kana-semana4-yoon", DECK_HIRA, [], [], False, True),
]


def registros(hira, kata, dakuten, yoon):
    saida = []
    if hira:
        saida += fonte.linhas_do_bloco([(n, c) for n, c in fonte.HIRAGANA if n in hira],
                                       "hiragana", "hira")
    if kata:
        saida += fonte.linhas_do_bloco([(n, c) for n, c in fonte.KATAKANA if n in kata],
                                       "katakana", "kata")
    if dakuten:
        saida += fonte.linhas_do_bloco(fonte.DAKUTEN_H, "hiragana", "dakuten")
    if yoon:
        saida += fonte.gerar_yoon()
    return saida


def main():
    os.makedirs("anki", exist_ok=True)
    total = 0
    for nome, deck, hira, kata, dak, yo in SEMANAS:
        regs = registros(hira, kata, dak, yo)
        destino = os.path.join("anki", nome + ".apkg")
        qtd = gerar_apkg(regs, deck, destino)
        print(f"{destino}: {qtd} notas ({qtd*2} cartoes)  ->  {deck}")
        total += qtd

    # O completo fica no deck PAI de proposito: ele mistura os dois sistemas e
    # so serve para quem quiser importar tudo de uma vez, sem separacao.
    completo = registros(["a","ka","sa","ta","na","ha","ma","ya","ra","wa"],
                         ["a","ka","sa","ta","na","ha","ma","ya","ra","wa"], True, True)
    destino = os.path.join("anki", "kana-fase0-completo.apkg")
    gerar_apkg(completo, DECK_PAI, destino)
    print(f"{destino}: {len(completo)} notas ({len(completo)*2} cartoes)  ->  {DECK_PAI}")

    print(f"\nsoma das semanas: {total} notas (deve bater com o completo: {len(completo)})")


if __name__ == "__main__":
    main()
