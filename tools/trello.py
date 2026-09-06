#!/usr/bin/env python3
"""
Ponte entre o repositorio e o Trello.

Existe para fechar o buraco que apareceu nos primeiros 8 dias: eu so sabia do
andamento aquilo que ele me contava na sessao, e o que ele esquecia de contar
(audio, importacao de deck) simplesmente sumia. Com isto, o /estudo le o board
no Passo 0 e escreve nele no Passo 4.

Subcomandos:
  setup                       cria a lista de pendencias e os checklists de mesa
  status                      imprime o andamento do board  (Passo 0 do /estudo)
  sync                        marca no Trello os dias ja registrados no diario
  pendencia "texto" [DD/MM]   cria um card em Pendencias, com vencimento opcional
  feito "trecho"              arquiva a pendencia que casa com o trecho

CREDENCIAIS: ~/.config/japones/trello.env, chmod 600, FORA do repositorio.
O repo e publico no GitHub — credencial dentro dele vaza mesmo com .gitignore.
Formato do arquivo:
    TRELLO_KEY=xxxx
    TRELLO_TOKEN=yyyy
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BOARD_ID = "6a70b97141db00bba4d1da55"
API = "https://api.trello.com/1"
CREDENCIAIS = os.path.expanduser("~/.config/japones/trello.env")

LISTA_PENDENCIAS = "⚡ Pendencias"
LISTA_AUDIO = "🎧 Audio (30 min/dia)"
CHECKLIST_MESA = "Mesa (1h)"

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIARIO = os.path.join(RAIZ, "progresso", "diario.md")

# (nome do card, primeira data, dias) — mesma divisao de plano/curriculo.md
SEMANAS = [
    ("Semana 1", ["03/08", "04/08", "05/08", "06/08", "07/08", "08/08", "09/08"]),
    ("Semana 2", ["10/08", "11/08", "12/08", "13/08", "14/08", "15/08", "16/08"]),
    ("Semana 3", ["17/08", "18/08", "19/08", "20/08", "21/08", "22/08", "23/08"]),
    ("Semana 4", ["24/08", "25/08", "26/08", "27/08", "28/08", "29/08", "30/08"]),
    ("Semana 5", ["31/08", "01/09", "02/09", "03/09", "04/09", "05/09", "06/09"]),
    ("Semana 6", ["07/09", "08/09", "09/09", "10/09", "11/09", "12/09", "13/09"]),
    ("Semana 7", ["14/09", "15/09", "16/09", "17/09", "18/09", "19/09", "20/09"]),
    ("Semana 8", ["21/09", "22/09", "23/09", "24/09", "25/09", "26/09", "27/09"]),
]
DIA_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]


def credenciais():
    if not os.path.exists(CREDENCIAIS):
        print(f"FALTA O ARQUIVO DE CREDENCIAIS: {CREDENCIAIS}\n\n"
              f"  mkdir -p ~/.config/japones\n"
              f"  printf 'TRELLO_KEY=SUA_KEY\\nTRELLO_TOKEN=SEU_TOKEN\\n' > {CREDENCIAIS}\n"
              f"  chmod 600 {CREDENCIAIS}\n", file=sys.stderr)
        sys.exit(2)
    dados = {}
    with open(CREDENCIAIS) as f:
        for linha in f:
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                dados[k.strip()] = v.strip()
    if not dados.get("TRELLO_KEY") or not dados.get("TRELLO_TOKEN"):
        print(f"{CREDENCIAIS} nao tem TRELLO_KEY e TRELLO_TOKEN", file=sys.stderr)
        sys.exit(2)
    return dados["TRELLO_KEY"], dados["TRELLO_TOKEN"]


def chamar(metodo, caminho, **params):
    key, token = CRED
    params.update({"key": key, "token": token})
    if metodo == "GET":
        req = urllib.request.Request(f"{API}{caminho}?{urllib.parse.urlencode(params)}")
    else:
        req = urllib.request.Request(f"{API}{caminho}",
                                     data=urllib.parse.urlencode(params).encode(),
                                     method=metodo)
    with urllib.request.urlopen(req) as r:
        corpo = r.read().decode()
        return json.loads(corpo) if corpo.strip() else {}


def listas():
    return {l["name"]: l["id"] for l in
            chamar("GET", f"/boards/{BOARD_ID}/lists", fields="name")}


def cards_do_board():
    return chamar("GET", f"/boards/{BOARD_ID}/cards", fields="name,desc,idList,due,dueComplete")


def checklists_do_card(id_card):
    return chamar("GET", f"/cards/{id_card}/checklists",
                  fields="name", checkItem_fields="name,state")


def sessoes_registradas():
    """Le as datas das sessoes ja feitas no diario. Fonte de verdade e o repo."""
    if not os.path.exists(DIARIO):
        return set()
    with open(DIARIO) as f:
        texto = f.read()
    # So conta entrada de sessao que aconteceu: as linhas de ausencia do diario
    # ("— **sem sessao de mesa**") ficam de fora de proposito.
    feitas = set()
    for m in re.finditer(r"^## \d{4}-(\d{2})-(\d{2}).*?—\s*\*{0,2}(?:completa|parcial)",
                         texto, re.M):
        mes, dia = m.groups()
        feitas.add(f"{dia}/{mes}")
    return feitas


# ---------------------------------------------------------------- setup

def setup():
    ls = listas()
    if LISTA_PENDENCIAS not in ls:
        ls[LISTA_PENDENCIAS] = chamar("POST", "/lists", name=LISTA_PENDENCIAS,
                                      idBoard=BOARD_ID, pos="bottom")["id"]
        print(f"lista criada: {LISTA_PENDENCIAS}")
    else:
        print(f"lista ja existe: {LISTA_PENDENCIAS}")

    cards = cards_do_board()
    for nome, datas in SEMANAS:
        card = next((c for c in cards if c["name"].startswith(nome + " (")), None)
        if not card:
            print(f"  ! card '{nome}' nao encontrado")
            continue
        atuais = checklists_do_card(card["id"])
        if any(c["name"] == CHECKLIST_MESA for c in atuais):
            print(f"  {nome}: checklist de mesa ja existe, preservado")
            continue
        cl = chamar("POST", "/checklists", idCard=card["id"], name=CHECKLIST_MESA)
        for i, d in enumerate(datas):
            chamar("POST", f"/checklists/{cl['id']}/checkItems",
                   name=f"{DIA_SEMANA[i]} {d}", pos="bottom")
        print(f"  {nome}: checklist de mesa criado (7 dias)")


# ---------------------------------------------------------------- sync

def sync():
    feitas = sessoes_registradas()
    if not feitas:
        print("nenhuma sessao encontrada no diario")
        return
    cards = cards_do_board()
    marcados = 0
    for nome, _ in SEMANAS:
        card = next((c for c in cards if c["name"].startswith(nome + " (")), None)
        if not card:
            continue
        for cl in checklists_do_card(card["id"]):
            if cl["name"] != CHECKLIST_MESA:
                continue
            for item in cl.get("checkItems", []):
                data = item["name"].split()[-1]
                if data in feitas and item["state"] != "complete":
                    chamar("PUT", f"/cards/{card['id']}/checkItem/{item['id']}",
                           state="complete")
                    print(f"  marcado: {nome} · {item['name']}")
                    marcados += 1
    print(f"\n{marcados} dia(s) marcado(s) a partir do diario.")


# ---------------------------------------------------------------- pendencia

def feito(trecho):
    """Arquiva a pendencia cujo nome contem o trecho. Arquivar, e nao apagar:
    o card sai da vista mas fica recuperavel se tiver sido fechado por engano."""
    ls = listas()
    achados = [c for c in chamar("GET", f"/lists/{ls[LISTA_PENDENCIAS]}/cards",
                                 fields="name")
               if trecho.lower() in c["name"].lower()]
    if not achados:
        print(f"nenhuma pendencia com '{trecho}'")
        return
    for c in achados:
        chamar("PUT", f"/cards/{c['id']}", dueComplete="true", closed="true")
        print(f"concluida: {c['name']}")


def pendencia(texto, vencimento=None):
    ls = listas()
    if LISTA_PENDENCIAS not in ls:
        print(f"rode primeiro: python3 tools/trello.py setup", file=sys.stderr)
        sys.exit(1)
    params = {"name": texto, "idList": ls[LISTA_PENDENCIAS], "pos": "top"}
    if vencimento:
        dia, mes = vencimento.split("/")
        ano = 2026 if int(mes) >= 8 else 2027
        params["due"] = f"{ano}-{mes}-{dia}T12:00:00.000Z"
    chamar("POST", "/cards", **params)
    print(f"pendencia criada: {texto}" + (f" (vence {vencimento})" if vencimento else ""))


# ---------------------------------------------------------------- status

def barra(feitos, total, largura=7):
    if not total:
        return ""
    cheio = round(feitos / total * largura)
    return "█" * cheio + "░" * (largura - cheio)


def status():
    ls = {v: k for k, v in listas().items()}
    cards = cards_do_board()
    por_lista = {}
    for c in cards:
        por_lista.setdefault(ls.get(c["idList"], "?"), []).append(c)

    print("=" * 60)
    print("TRELLO — andamento")
    print("=" * 60)

    for nome_lista in ["🔄 Semana atual", LISTA_AUDIO, LISTA_PENDENCIAS,
                       "📅 Avisos do JLPT"]:
        cs = por_lista.get(nome_lista, [])
        if not cs and nome_lista != LISTA_PENDENCIAS:
            continue
        print(f"\n▸ {nome_lista}")
        if not cs:
            print("   (vazia)")
            continue
        for c in cs[:8]:
            due = ""
            if c.get("due"):
                due = f"  [vence {c['due'][8:10]}/{c['due'][5:7]}]"
                if c.get("dueComplete"):
                    due += " ✓"
            print(f"   • {c['name'][:52]}{due}")
            for cl in checklists_do_card(c["id"]):
                itens = cl.get("checkItems", [])
                if not itens:
                    continue
                ok = sum(1 for i in itens if i["state"] == "complete")
                pend = [i["name"] for i in itens if i["state"] != "complete"]
                print(f"       {cl['name']:12s} {barra(ok, len(itens))} {ok}/{len(itens)}"
                      + (f"   falta: {', '.join(pend[:4])}" if pend else "   ✅"))

    print()


def main():
    global CRED
    if len(sys.argv) < 2 or sys.argv[1] not in ("setup", "status", "sync", "pendencia", "feito"):
        print(__doc__)
        sys.exit(1)
    CRED = credenciais()
    cmd = sys.argv[1]
    if cmd == "setup":
        setup()
    elif cmd == "status":
        status()
    elif cmd == "sync":
        sync()
    elif cmd == "pendencia":
        if len(sys.argv) < 3:
            print('uso: python3 tools/trello.py pendencia "texto" [DD/MM]', file=sys.stderr)
            sys.exit(1)
        pendencia(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "feito":
        if len(sys.argv) < 3:
            print('uso: python3 tools/trello.py feito "trecho do nome"', file=sys.stderr)
            sys.exit(1)
        feito(sys.argv[2])


if __name__ == "__main__":
    main()
