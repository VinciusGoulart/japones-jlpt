"""Regras do estudo que não dependem de fonte nenhuma: o relógio e o streak."""
from datetime import date, datetime, timedelta

from japones import config


def dia_de_estudo(agora: datetime | None = None) -> date:
    """O dia vira às 04:00: uma sessão às 01:27 de sábado conta como sexta."""
    agora = agora or datetime.now()
    return (agora - timedelta(hours=config.ROLLOVER_H)).date()


def intervalo_do_dia(d: date) -> tuple[datetime, datetime]:
    """[04:00 do dia, 04:00 do dia seguinte) — a janela de um dia de estudo."""
    ini = datetime.combine(d, datetime.min.time()) + timedelta(hours=config.ROLLOVER_H)
    return ini, ini + timedelta(days=1)


def streak(datas_com_aula: set[date], hoje: date) -> tuple[int, int]:
    """(atual, recorde). Atual termina hoje ou ontem — a aula de hoje pode não ter
    acontecido ainda, e isso não quebra a sequência antes da hora."""
    atual = 0
    d = hoje if hoje in datas_com_aula else hoje - timedelta(days=1)
    while d in datas_com_aula:
        atual += 1
        d -= timedelta(days=1)

    recorde = corrente = 0
    anterior = None
    for d in sorted(datas_com_aula):
        corrente = corrente + 1 if anterior and d - anterior == timedelta(days=1) else 1
        recorde = max(recorde, corrente)
        anterior = d
    return atual, recorde


def ano_de(dia: int, mes: int, referencia: date) -> date:
    """DD/MM sem ano: o ano que deixa a data mais perto da referência.
    O plano vai de ago/2026 a dez/2027, então "03/01" é 2027 e "03/08" depende."""
    candidatas = []
    for k in (-1, 0, 1):
        try:
            candidatas.append(date(referencia.year + k, mes, dia))
        except ValueError:      # 29/02 em ano que não é bissexto
            pass
    if not candidatas:
        raise ValueError(f"data inválida: {dia:02d}/{mes:02d}")
    return min(candidatas, key=lambda c: abs((c - referencia).days))
