"""O board do Trello em dados (o tools/trello.py imprime; este devolve dicionários).

O Trello continua sendo o principal para pendências e cobranças: aqui só se LÊ.
Escrever (criar pendência, marcar áudio) segue pelo tools/trello.py, que é o
caminho que já tem as credenciais, o formato de data e o histórico de uso.
Uma chamada só (cards com checklists embutidos): o hoje() não pode esperar
uma requisição por card.
"""
import importlib.util
import socket
from datetime import date, datetime

from japones import config


class TrelloIndisponivel(Exception):
    pass


# Neste PC a consulta AAAA (IPv6) do DNS não responde e o glibc espera 5 s antes
# de desistir — na PRIMEIRA requisição de cada processo (medido em 17/10:
# getaddrinfo com AF_UNSPEC 5,04 s; com AF_INET 0,02 s). Como api.trello.com só
# tem IPv4 mesmo, a busca do Trello pede só o A. Restrito a este host de propósito.
_getaddrinfo_original = socket.getaddrinfo


def _getaddrinfo_ipv4_trello(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0 and isinstance(host, str) and host.endswith("trello.com"):
        family = socket.AF_INET
    return _getaddrinfo_original(host, port, family, type, proto, flags)


socket.getaddrinfo = _getaddrinfo_ipv4_trello


def _ferramenta():
    spec = importlib.util.spec_from_file_location("trello_tool", config.TOOLS / "trello.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        mod.CRED = mod.credenciais()
    except SystemExit as e:
        raise TrelloIndisponivel("credenciais do Trello ausentes em ~/.config/japones/trello.env") from e
    return mod


def _vencimento(due: str | None) -> str | None:
    # O tools/trello.py grava o vencimento às 12:00Z: a data UTC é a data pretendida.
    return due[:10] if due else None


def board(hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    tool = _ferramenta()
    try:
        nomes = {l["id"]: l["name"] for l in
                 tool.chamar("GET", f"/boards/{tool.BOARD_ID}/lists", fields="name")}
        cards = tool.chamar("GET", f"/boards/{tool.BOARD_ID}/cards",
                            fields="name,idList,due,dueComplete,shortUrl,dateLastActivity",
                            checklists="all", checklist_fields="name")
    except Exception as e:  # rede, token revogado…
        raise TrelloIndisponivel(f"falha ao ler o board: {e}") from e

    por_lista: dict[str, list] = {}
    for c in cards:
        venc = _vencimento(c.get("due"))
        checklists = []
        for cl in c.get("checklists", []):
            itens = cl.get("checkItems", [])
            checklists.append({
                "nome": cl["name"],
                "feitos": sum(1 for i in itens if i["state"] == "complete"),
                "total": len(itens),
                "faltam": [i["name"] for i in sorted(itens, key=lambda i: i.get("pos", 0))
                           if i["state"] != "complete"],
            })
        por_lista.setdefault(nomes.get(c["idList"], "?"), []).append({
            "nome": c["name"],
            "url": c.get("shortUrl"),
            "vence": venc,
            "concluido": bool(c.get("dueComplete")),
            "vencido": bool(venc and not c.get("dueComplete") and venc < hoje.isoformat()),
            "checklists": checklists,
        })
    return {"lido_em": datetime.now().isoformat(timespec="seconds"), "listas": por_lista,
            "url_board": f"https://trello.com/b/{tool.BOARD_ID}"}


def pendencias(b: dict) -> list[dict]:
    return sorted(b["listas"].get("⚡ Pendencias", []), key=lambda c: c["vence"] or "9999")


def semana_atual(b: dict) -> list[dict]:
    return b["listas"].get("🔄 Semana atual", [])
