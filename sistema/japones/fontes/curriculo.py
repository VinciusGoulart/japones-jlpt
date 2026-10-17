"""As tabelas de plano/curriculo.md viram o calendário do que vem.

O currículo é replanejado acrescentando tabelas novas (Semana 6 replanejada,
Semana 7…), e a mesma data pode aparecer em mais de uma. Vale a linha MAIS
NOVA, ou seja, a última do arquivo para aquela data.
"""
import re
from datetime import date, timedelta

from japones import config
from japones.dominio import ano_de

# | 68 | sex 16/10 | conteúdo |
_LINHA = re.compile(r"^\|\s*(\d+)\s*\|\s*(\S{3})\.?\s+(\d{1,2})/(\d{1,2})\s*\|\s*(.+?)\s*\|\s*$", re.M)


def linhas(texto: str | None = None, referencia: date | None = None) -> list[dict]:
    if texto is None:
        texto = config.CURRICULO.read_text()
    referencia = referencia or config.INICIO_PLANO
    saida = []
    for m in _LINHA.finditer(texto):
        dia_plano, semana_txt, dd, mm, conteudo = m.groups()
        try:
            d = ano_de(int(dd), int(mm), referencia)
        except ValueError:
            continue
        referencia = d  # o arquivo anda no tempo; a próxima linha está perto desta
        saida.append({"dia_plano": int(dia_plano), "data": d.isoformat(),
                      "dia_semana": semana_txt, "conteudo": conteudo,
                      "linha": texto.count("\n", 0, m.start()) + 1})
    return saida


def por_data(texto: str | None = None) -> dict[str, dict]:
    """data -> a linha mais nova do plano para ela."""
    plano = {}
    for l in linhas(texto):
        plano[l["data"]] = l
    return plano


def do_dia(d: date, texto: str | None = None) -> dict | None:
    return por_data(texto).get(d.isoformat())


def proximos(d: date, dias: int = 7, texto: str | None = None) -> list[dict]:
    plano = por_data(texto)
    return [plano[k] for k in ((d + timedelta(days=i)).isoformat() for i in range(dias)) if k in plano]
