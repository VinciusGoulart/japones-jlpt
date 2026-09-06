#!/usr/bin/env python3
"""
Gera anki/vocabulario-fase0.apkg a partir de progresso/vocabulario.tsv e anexa
ao card de pendencia do Trello.

POR QUE EXISTE: o AnkiDroid nao importa TSV, so .apkg/.colpkg — fato documentado
em anexar_decks_trello.py desde 11/08 e ESQUECIDO quando a cobranca de importacao
foi criada apontando para o proprio .tsv (duas sessoes cobradas em vao, 26-28/08).
O TSV segue sendo a fonte de verdade no repositorio; o .apkg e a entrega
para o celular.

Diferencas em relacao aos decks de kana (gerar_apkg.py):
  - UM cartao por nota (palavra -> leitura/significado), como o #notetype:Basic
    do cabecalho do TSV. Producao ativa e trabalho da mesa, nao do deck.
  - Modelo proprio (SEMENTE_VOCAB), congelado como o dos kana e pelo mesmo
    motivo: mudar o model_id de notas ja importadas aborta a reimportacao.
  - guid com prefixo "vocab::" — reimportar atualiza a nota, nunca duplica.
  - OS DIAS MAIS RECENTES ENTRAM PRIMEIRO na fila de cartoes novos: e o material
    da semana corrente (e da prova); o vocabulario antigo, que ele ja domina,
    preenche depois. Cartoes ja importados nao mudam de lugar na reimportacao.

Uso:  python3 tools/gerar_vocab_apkg.py            # gera e anexa no Trello
      python3 tools/gerar_vocab_apkg.py --so-gerar  # so gera o arquivo
"""
import json
import os
import re
import sqlite3
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_apkg as base

TSV = "progresso/vocabulario.tsv"
SAIDA = "anki/vocabulario-fase0.apkg"
DECK = "Japonês::Vocabulário"
CARD_PREFIXO = "Importar vocabul"

# Quantos dias de mesa ficam no topo da fila de novos (a "semana corrente").
JANELA_RECENTES = 3

# CONGELADO, como o SEMENTE_MODELO dos kana. Nao mudar nunca.
SEMENTE_VOCAB = "model::Japonês::Vocabulário::Basic"

CSS = (
    ".card { font-family: arial; font-size: 36px; text-align: center; "
    "color: black; background-color: white; }"
)


def guid_vocab(frente):
    import hashlib
    return hashlib.sha1(("vocab::" + frente).encode("utf-8")).hexdigest()[:20]


def montar_modelo_basico(model_id, deck_id):
    return {
        str(model_id): {
            "id": model_id, "name": "Vocabulário (palavra → sentido)", "type": 0,
            "mod": int(time.time()), "usn": -1, "sortf": 0, "did": deck_id,
            "tmpls": [
                {"name": "Reconhecer", "ord": 0,
                 "qfmt": "{{Front}}",
                 "afmt": "{{FrontSide}}<hr id=answer>{{Back}}",
                 "did": None, "bqfmt": "", "bafmt": ""},
            ],
            "flds": [
                {"name": "Front", "ord": 0, "sticky": False, "rtl": False,
                 "font": "Arial", "size": 20, "media": []},
                {"name": "Back", "ord": 1, "sticky": False, "rtl": False,
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
            frente, verso = partes[0], partes[1]
            tags = partes[2] if len(partes) > 2 else "fase0 vocab"
            registros.append((frente, verso, tags))
    return registros


def dia_da_tag(tags):
    m = re.search(r"dia(\d+)", tags)
    return int(m.group(1)) if m else 0


def ordenar_recentes_primeiro(registros):
    """Janela dos ultimos JANELA_RECENTES dias primeiro; o resto na ordem do arquivo."""
    max_dia = max((dia_da_tag(t) for _, _, t in registros), default=0)
    corte = max_dia - (JANELA_RECENTES - 1)
    recentes = [r for r in registros if dia_da_tag(r[2]) >= corte]
    antigos = [r for r in registros if dia_da_tag(r[2]) < corte]
    return recentes + antigos, len(recentes)


def gerar(registros):
    agora = int(time.time())
    agora_ms = agora * 1000
    deck_id = base.id_estavel("deck::" + DECK, 1600000000000)
    model_id = base.id_estavel(SEMENTE_VOCAB, 1700000000000)

    tmp_db = SAIDA + ".tmp.anki2"
    if os.path.exists(tmp_db):
        os.remove(tmp_db)

    con = sqlite3.connect(tmp_db)
    con.executescript(base.ESQUEMA)
    con.execute(
        "INSERT INTO col VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (1, agora, agora_ms, agora_ms, 11, 0, 0, 0,
         json.dumps(base.CONF_COL),
         json.dumps(montar_modelo_basico(model_id, deck_id)),
         json.dumps(base.montar_deck(deck_id, DECK)),
         json.dumps(base.CONF_DECK),
         json.dumps({})),
    )

    base_notas = agora_ms
    base_cartoes = agora_ms + 5_000_000
    for posicao, (frente, verso, tags) in enumerate(registros):
        nota_id = base_notas + posicao
        campos = frente + base.SEPARADOR + verso
        con.execute(
            "INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (nota_id, guid_vocab(frente), model_id, agora, -1,
             " " + tags.strip() + " ", campos, frente,
             base.csum_do_campo(frente), 0, ""),
        )
        con.execute(
            "INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (base_cartoes + posicao, nota_id, deck_id, 0, agora, -1,
             0, 0, posicao, 0, 0, 0, 0, 0, 0, 0, 0, ""),
        )

    con.commit()
    con.close()
    with zipfile.ZipFile(SAIDA, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tmp_db, "collection.anki2")
        z.writestr("media", "{}")
    os.remove(tmp_db)


def descricao(total, recentes):
    return "\n".join([
        "### Importar no AnkiDroid",
        f"- 📎 Toque no anexo `vocabulario-fase0.apkg` → o AnkiDroid abre e importa.",
        f"- Deck: `{DECK}` — {total} palavras das sessões de mesa, 1 cartão por palavra.",
        f"- As {recentes} palavras dos dias MAIS RECENTES entram primeiro na fila de novos.",
        "- Sugestão: 20 novos/dia neste deck (são palavras já vistas na mesa — revisão leve).",
        "  Se pesar junto com o Kaishi, reduza.",
        "- Reimportar versões novas deste arquivo NÃO duplica: só acrescenta as novas.",
        "- O `.tsv` do repositório é a fonte; este `.apkg` é a entrega para o celular.",
    ])


ANKICONNECT = "http://127.0.0.1:8765"


def ankiconnect(action, **params):
    import urllib.request
    corpo = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKICONNECT, data=corpo)
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read().decode())
    if resp.get("error"):
        raise RuntimeError(resp["error"])
    return resp.get("result")


def importar_direto():
    """Importa via AnkiConnect (Anki desktop ABERTO) e dispara o sync.

    E o caminho principal desde 30/08: o proprio Anki faz a importacao pelo
    codigo oficial dele — este script nunca escreve na colecao. Devolve False
    se o Anki nao estiver aberto (e o Trello vira o fallback).
    """
    try:
        ankiconnect("version")
    except Exception:
        return False
    ankiconnect("importPackage", path=os.path.abspath(SAIDA))
    ankiconnect("sync")
    return True


def anexar_no_trello(total, recentes):
    import trello
    import anexar_decks_trello as adt
    key, token = trello.credenciais()

    cards = adt.get(f"/boards/{adt.BOARD_ID}/cards", key, token, fields="name")
    card = next((c for c in cards if c["name"].startswith(CARD_PREFIXO)), None)
    if not card:
        print("  ! card de importacao nao encontrado no board — anexo nao enviado")
        return

    atuais = adt.get(f"/cards/{card['id']}/attachments", key, token, fields="name")
    for a in atuais:
        if a["name"].endswith((".apkg", ".tsv")):
            adt.delete(f"/cards/{card['id']}/attachments/{a['id']}", key, token)
            print(f"  removido anexo antigo: {a['name']}")

    nome_arquivo = os.path.basename(SAIDA)
    if adt.anexar(card["id"], SAIDA, nome_arquivo, key, token):
        print(f"  anexado: {nome_arquivo} ({os.path.getsize(SAIDA)} bytes)")
    else:
        print(f"  ! falha ao anexar {nome_arquivo}")
        return

    adt.put(f"/cards/{card['id']}", key, token,
            name=f"Importar vocabulario-fase0.apkg no AnkiDroid ({total} palavras — anexo aqui)",
            desc=descricao(total, recentes))
    print("  card renomeado e descricao atualizada")


def main():
    registros, recentes = ordenar_recentes_primeiro(ler_tsv())
    gerar(registros)
    total = len(registros)
    print(f"{SAIDA}: {total} notas ({total} cartoes, 1 por palavra)  ->  {DECK}")
    print(f"  {recentes} palavras dos ultimos {JANELA_RECENTES} dias de mesa na frente da fila")
    if "--so-gerar" not in sys.argv:
        if importar_direto():
            print("  importado direto no Anki do PC (AnkiConnect) + sync AnkiWeb disparado")
            print("  o celular recebe no proximo sync do AnkiDroid; Trello dispensado")
        else:
            print("  Anki do PC fechado — caindo para o anexo no Trello")
            anexar_no_trello(total, recentes)


if __name__ == "__main__":
    main()
