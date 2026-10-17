"""Leitura e escrita (só append) do progresso/diario.md.

O diário é a narrativa: é o que ele lê, e nada nele é editado depois. Daqui sai
a estrutura de cada entrada (tipo, placar, horário) para o estudo.db. O formato
mudou ao longo das semanas — as primeiras entradas não têm "Início" nem placar
em cabeçalho —, então tudo que não casa vira None, nunca um palpite.
"""
import re
from datetime import date

from japones import config

_CABECALHO = re.compile(r"^## (\d{4}-\d{2}-\d{2})(.*)$", re.M)
_DIA = re.compile(r"\(dia (\d+) do plano\)")
_MINUTOS = re.compile(r"\*\*Tempo:\*\*\s*~?(\d+)\s*min")
_INICIO = re.compile(r"In[íi]cio:?\**\s*~?(\d{1,2})[:h](\d{2})")
_FASE = re.compile(r"\*\*Fase:\*\*\s*(\d+)")
_SEMANA = re.compile(r"\*\*Fase:\*\*[^\n]*?semana (\d+)")
_VERIF = re.compile(r"^###\s*Verifica[çc][ãa]o[^\n]*?(\d+)\s*(?:de|/)\s*(\d+)", re.M)
_PROD = re.compile(r"^###\s*Produ[çc][ãa]o[^\n]*?(\d+)\s*(?:de|/)\s*(\d+)", re.M)


def _tipo(resto: str) -> str:
    r = resto.lower()
    if "parcial" in r:
        return "parcial"
    if "sem sessão de mesa" in r or "sem sessao de mesa" in r or "sem mesa" in r:
        return "sem_mesa"
    return "completa"


def _titulo(resto: str) -> str | None:
    if "·" not in resto:
        return None
    return resto.split("·", 1)[1].strip().strip("*").strip() or None


def _int(m, g=1):
    return int(m.group(g)) if m else None


def entradas(texto: str | None = None) -> list[dict]:
    """Todas as entradas, na ordem do arquivo."""
    if texto is None:
        texto = config.DIARIO.read_text()
    marcas = list(_CABECALHO.finditer(texto))
    saida = []
    for i, m in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        bloco = texto[m.start():fim].rstrip()
        # o separador '---' das primeiras semanas não faz parte da entrada
        bloco = re.sub(r"\n-{3,}\s*$", "", bloco).rstrip()
        data_txt, resto = m.group(1), m.group(2)
        inicio = _INICIO.search(bloco)
        verif, prod = _VERIF.search(bloco), _PROD.search(bloco)
        saida.append({
            "data": data_txt,
            "dia_plano": _int(_DIA.search(resto)),
            "tipo": _tipo(resto),
            "titulo": _titulo(resto),
            "fase": _int(_FASE.search(bloco)),
            "semana": _int(_SEMANA.search(bloco)),
            "inicio": f"{int(inicio.group(1)):02d}:{inicio.group(2)}" if inicio else None,
            "minutos": _int(_MINUTOS.search(bloco)),
            "verif_ok": _int(verif, 1), "verif_total": _int(verif, 2),
            "prod_ok": _int(prod, 1), "prod_total": _int(prod, 2),
            "texto_md": bloco,
        })
    return saida


def datas_registradas(texto: str | None = None) -> set[str]:
    return {e["data"] for e in entradas(texto)}


def acrescentar(texto_md: str) -> None:
    """Append da entrada no fim do diário. Nunca reescreve o que já está lá."""
    texto_md = texto_md.strip()
    if not texto_md.startswith("## "):
        raise ValueError("a entrada do diário começa com '## AAAA-MM-DD ...'")
    atual = config.DIARIO.read_text() if config.DIARIO.exists() else ""
    # exatamente uma linha em branco entre a entrada anterior e a nova
    if not atual or atual.endswith("\n\n"):
        separador = ""
    elif atual.endswith("\n"):
        separador = "\n"
    else:
        separador = "\n\n"
    with open(config.DIARIO, "a") as f:
        f.write(separador + texto_md + "\n")


def data_de(entrada: dict) -> date:
    return date.fromisoformat(entrada["data"])
