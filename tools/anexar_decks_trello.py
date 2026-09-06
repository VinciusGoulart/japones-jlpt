#!/usr/bin/env python3
"""
Pipeline completo dos decks: gera os .apkg e anexa cada um ao card da sua semana
no Trello, removendo anexos antigos que tenham virado obsoletos.

O AnkiDroid importa .apkg/.colpkg, NAO importa TSV -- por isso os TSV antigos sao
removidos dos cards. Os .tsv continuam no repositorio para quem usar Anki desktop.

Uso: python3 tools/anexar_decks_trello.py <TRELLO_KEY> <TRELLO_TOKEN>
"""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_apkg

BOARD_ID = "6a70b97141db00bba4d1da55"
API = "https://api.trello.com/1"

# card -> lista de (arquivo .apkg, quantidade de notas)
# A Semana 4 tem dois arquivos porque os yoon sao HIRAGANA e os 11 kana que
# faltam sao katakana: cada um vai para o seu subdeck.
POR_SEMANA = [
    ("Semana 1", [("kana-semana1-hiragana-parte1.apkg", 35),
                  ("kana-fase0-completo.apkg", 150)]),
    ("Semana 2", [("kana-semana2-hiragana-parte2.apkg", 36)]),
    ("Semana 3", [("kana-semana3-katakana-parte1.apkg", 35)]),
    ("Semana 4", [("kana-semana4-katakana-parte2.apkg", 11),
                  ("kana-semana4-yoon.apkg", 33)]),
]

MARCA = "### Trajeto (2h/dia, Anki no celular)"


def get(caminho, key, token, **kw):
    kw.update(key=key, token=token)
    url = f"{API}{caminho}?{urllib.parse.urlencode(kw)}"
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode())


def put(caminho, key, token, **kw):
    kw.update(key=key, token=token)
    req = urllib.request.Request(f"{API}{caminho}",
                                 data=urllib.parse.urlencode(kw).encode(), method="PUT")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def delete(caminho, key, token):
    req = urllib.request.Request(f"{API}{caminho}?key={key}&token={token}", method="DELETE")
    with urllib.request.urlopen(req) as r:
        return r.status


def anexar(card_id, caminho, nome, key, token):
    url = f"{API}/cards/{card_id}/attachments?key={key}&token={token}"
    proc = subprocess.run(
        ["curl", "-s", "-X", "POST", url, "-F", f"file=@{caminho}", "-F", f"name={nome}"],
        capture_output=True, text=True)
    try:
        return "id" in json.loads(proc.stdout)
    except Exception:
        return False


def bloco_anki(arquivos):
    linhas = [MARCA, "- 📎 **Baixe o(s) anexo(s) deste card e importe no AnkiDroid:**"]
    for nome, qtd in arquivos:
        linhas.append(f"  - `{nome}` — {qtd} notas ({qtd*2} cartoes: reconhecer + produzir)")
    linhas += [
        "- Importar e direto: toque no anexo, o AnkiDroid abre e pergunta se quer importar.",
        "- Todos caem no baralho `Japonês::Fase 0 - Kana`. Reimportar NAO duplica.",
        "- Deixe 5 cartoes novos/dia: o baralho segue a ordem do curriculo sozinho.",
        "- Alem do Anki: 30 min de audio (Nihongo con Teppei for Beginners, do ep. 1).",
    ]
    return "\n".join(linhas)


def main():
    # Credenciais: argumentos, ou o arquivo em ~/.config/japones/trello.env
    if len(sys.argv) >= 3:
        key, token = sys.argv[1], sys.argv[2]
    else:
        import trello
        key, token = trello.credenciais()

    print("=== 1. gerando os .apkg ===")
    gerar_apkg.main()

    print("\n=== 2. sincronizando anexos no Trello ===")
    cards = get(f"/boards/{BOARD_ID}/cards", key, token, fields="name,desc")

    for prefixo, esperados in POR_SEMANA:
        card = next((c for c in cards if c["name"].startswith(prefixo + " ")), None)
        if not card:
            print(f"  ! card '{prefixo}' nao encontrado")
            continue

        atuais = get(f"/cards/{card['id']}/attachments", key, token, fields="name")
        nomes_esperados = {n for n, _ in esperados}

        # remove obsoletos: .tsv (nao importa no celular) e .apkg que sairam da lista
        # (o kana-semana4-katakana-parte2 antigo tinha 44 notas e virou dois arquivos)
        for a in atuais:
            if a["name"].endswith(".tsv") or (
                    a["name"].endswith(".apkg") and a["name"] not in nomes_esperados):
                delete(f"/cards/{card['id']}/attachments/{a['id']}", key, token)
                print(f"  {prefixo}: removido anexo obsoleto {a['name']}")

        # Substitui sempre: o nome pode ser o mesmo e o conteudo ter mudado
        # (foi o que aconteceu ao repartir as semanas de 5 para 7 dias).
        por_nome = {a["name"]: a["id"] for a in atuais}
        for nome, _ in esperados:
            caminho = os.path.join("anki", nome)
            tamanho = os.path.getsize(caminho)
            if nome in por_nome:
                delete(f"/cards/{card['id']}/attachments/{por_nome[nome]}", key, token)
            if anexar(card["id"], caminho, nome, key, token):
                print(f"  {prefixo}: {nome} enviado ({tamanho} bytes)")
            else:
                print(f"  ! {prefixo}: falha ao anexar {nome}")

    print("\n=== 3. conferencia ===")
    for c in sorted(get(f"/boards/{BOARD_ID}/cards", key, token, fields="name"),
                    key=lambda x: x["name"]):
        for a in get(f"/cards/{c['id']}/attachments", key, token, fields="name,bytes"):
            print(f"  {c['name'][:34]:36s} 📎 {a['name']:38s} {a['bytes']:>7} bytes")


if __name__ == "__main__":
    main()
