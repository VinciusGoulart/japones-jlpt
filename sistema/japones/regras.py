"""Caderno de regras de gramática: a agenda de revisão espaçada e o importador (DESIGN §13).

Por que existe (23/10/2026, pedido dele): ele esquecia regras antigas (てもいいですか, まだ)
e, ao aplicar a regra nova, esquecia a outra na mesma frase. O vocabulário tinha o Anki;
a gramática não tinha agenda nenhuma — cada regra era ensinada uma vez e só voltava se
desse erro. Aqui cada regra ganha uma data de próxima revisão, que os exercícios movem.

    python -m japones.regras importar plano/regras.json [--por-dia 5]
"""
import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

from japones import db, dominio

TETO_DIAS = 60      # §13.2: depois de 30 dias, a regra volta a cada dois meses, nunca menos
POR_DIA = 5         # §13.3: a primeira revisão das regras importadas, espalhada


# ------------------------------------------------------------------ agenda (§13.2)

def _crescer(intervalo: float) -> float:
    """2, 5, 12, 30, 60: round() do Python arredonda 12,5 para 12 (para o par), o que fecha a sequência."""
    return 2 if intervalo < 2 else min(TETO_DIAS, round(intervalo * 2.5))


def agendar(con: sqlite3.Connection, regra_id: int, veredito: str, dia: date) -> None:
    """Move a agenda de uma regra pelo veredito de um exercício. Não faz commit: quem chama decide.

    Um erro no dia segura a regra para amanhã, e vários acertos no mesmo dia contam uma vez só:
    acertar 5 exercícios da mesma regra numa lição não é prova de que ela fixou.

    O erro entra como LACUNA na hora, mesmo quando o exercício tem dica e a 2ª tentativa ainda
    vai acontecer (§9.6): ela pode nunca vir (aba fechada), e adiar a conta faria o erro sumir da
    agenda. Se a 2ª sair certa, deslize() reclassifica com o que fica guardado aqui (23/10/2026)."""
    r = con.execute("SELECT intervalo, ultima_revisao, ultima_falha, intervalo_dia, lacunas_dia FROM regra WHERE id = ?",
                    (regra_id,)).fetchone()
    if not r or veredito not in ("certo", "errado"):
        return
    d = dia.isoformat()
    # O primeiro evento do dia guarda o intervalo de antes do dia: é dele que o deslize recua,
    # mesmo que um acerto do mesmo dia já o tenha feito crescer.
    if r["ultima_revisao"] != d:
        intervalo_dia, lacunas = r["intervalo"], 0
    else:
        intervalo_dia, lacunas = r["intervalo_dia"], r["lacunas_dia"]
    if veredito == "errado":
        con.execute("""UPDATE regra SET intervalo = 1, proxima = ?, erros = erros + 1, ultima_falha = ?,
                       ultima_revisao = ?, intervalo_dia = ?, lacunas_dia = ? WHERE id = ?""",
                    ((dia + timedelta(days=1)).isoformat(), d, d, intervalo_dia, lacunas + 1, regra_id))
        return
    if d in (r["ultima_falha"], r["ultima_revisao"]):
        intervalo = r["intervalo"]
    else:
        intervalo = _crescer(r["intervalo"])
    proxima = dia + timedelta(days=max(1, int(intervalo)))
    con.execute("""UPDATE regra SET acertos = acertos + 1, intervalo = ?, proxima = ?, ultima_revisao = ?,
                   intervalo_dia = ?, lacunas_dia = ? WHERE id = ?""",
                (intervalo, proxima.isoformat(), d, intervalo_dia, lacunas, regra_id))


def recuar(intervalo: float) -> int:
    """Um degrau para trás na sequência 2, 5, 12, 30, 60: 12 → 5, 30 → 12, 5 → 2, 2 → 1."""
    return max(1, round(intervalo / 2.5))


def deslize(con: sqlite3.Connection, regra_id: int, dia_falha: date) -> None:
    """A 2ª tentativa depois da dica saiu certa: o erro da 1ª resposta vira DESLIZE (§13.2). Sem commit.

    Por que (23/10/2026, recomendação do relatório de pesquisa aprovada por ele): quem se corrige
    com uma dica sabe a regra e falhou sob carga. Uma regra madura que escorregou uma vez recua um
    degrau, em vez de voltar ao zero como a lacuna (o erro que ele não sabe corrigir).

    O pior resultado do dia vence: se houve outra lacuna da mesma regra no dia, ela segura a regra
    em 1. Se a agenda já andou num dia posterior, só os contadores mudam."""
    r = con.execute("SELECT intervalo, ultima_revisao, ultima_falha, intervalo_dia, lacunas_dia FROM regra WHERE id = ?",
                    (regra_id,)).fetchone()
    if not r:
        return
    d = dia_falha.isoformat()
    # `erros` passa a contar só lacunas: o deslize sai de lá e vai para o contador dele
    con.execute("UPDATE regra SET erros = MAX(erros - 1, 0), deslizes = deslizes + 1 WHERE id = ?", (regra_id,))
    if r["ultima_falha"] != d or r["ultima_revisao"] != d:
        return
    lacunas = max(0, r["lacunas_dia"] - 1)
    if lacunas:
        con.execute("UPDATE regra SET lacunas_dia = ? WHERE id = ?", (lacunas, regra_id))
        return
    # intervalo_dia nulo = regra sem evento desde o esquema 5: o atual (1, depois da lacuna) é o lado seguro
    base = r["intervalo_dia"] if r["intervalo_dia"] is not None else r["intervalo"]
    intervalo = recuar(base)
    con.execute("UPDATE regra SET lacunas_dia = 0, intervalo = ?, proxima = ? WHERE id = ?",
                (intervalo, (dia_falha + timedelta(days=intervalo)).isoformat(), regra_id))


# ------------------------------------------------------------------ gravação

def _validar(item: dict, onde: str = "") -> dict:
    """Levanta ValueError com o que está errado. Devolve só os campos do contrato."""
    if not isinstance(item, dict):
        raise ValueError(f"{onde}cada regra é um objeto {{slug, titulo, ...}}")
    slug, titulo = item.get("slug"), item.get("titulo")
    if not isinstance(slug, str) or not slug.strip() or any(c.isspace() for c in slug.strip()):
        raise ValueError(f"{onde}'slug' é um texto sem espaços (ex. 'te-mo-ii')")
    if not isinstance(titulo, str) or not titulo.strip():
        raise ValueError(f"{onde}falta 'titulo'")
    for campo in ("categoria", "explicacao_md", "ensinada_em"):
        if item.get(campo) is not None and not isinstance(item[campo], str):
            raise ValueError(f"{onde}'{campo}' é texto")
    if item.get("ensinada_em"):
        try:
            date.fromisoformat(item["ensinada_em"])
        except ValueError:
            raise ValueError(f"{onde}'ensinada_em' é AAAA-MM-DD, veio {item['ensinada_em']!r}") from None
    return {"slug": slug.strip(), "titulo": titulo.strip(), "categoria": item.get("categoria") or None,
            "explicacao_md": item.get("explicacao_md") or None, "ensinada_em": item.get("ensinada_em") or None}


def _upsert(con, r: dict, proxima_nova: str | None) -> bool:
    """Grava pelo slug; True se a regra é nova. Campo None não apaga o que existe, e a agenda
    de uma regra existente nunca é tocada: reimportar o caderno não zera o que ele já revisou."""
    nova = con.execute("SELECT 1 FROM regra WHERE slug = ?", (r["slug"],)).fetchone() is None
    con.execute("""INSERT INTO regra (slug, titulo, categoria, ensinada_em, explicacao_md, proxima)
                   VALUES (:slug, :titulo, :categoria, :ensinada_em, :explicacao_md, :proxima)
                   ON CONFLICT(slug) DO UPDATE SET
                     titulo        = excluded.titulo,
                     categoria     = COALESCE(excluded.categoria, regra.categoria),
                     ensinada_em   = COALESCE(excluded.ensinada_em, regra.ensinada_em),
                     explicacao_md = COALESCE(excluded.explicacao_md, regra.explicacao_md)""",
                {**r, "proxima": proxima_nova})
    return nova


def salvar(con, slug: str, titulo: str, categoria: str | None = None, explicacao_md: str | None = None,
           ensinada_em: str | None = None, dia: date | None = None) -> dict:
    """Upsert de uma regra (o salvar_regra do MCP). Regra nova nasce com intervalo 0 e
    a primeira revisão amanhã: ensinada hoje, revisada amanhã."""
    r = _validar({"slug": slug, "titulo": titulo, "categoria": categoria, "explicacao_md": explicacao_md,
                  "ensinada_em": ensinada_em})
    dia = dia or dominio.dia_de_estudo()
    nova = _upsert(con, r, (dia + timedelta(days=1)).isoformat())
    con.commit()
    proxima = con.execute("SELECT proxima FROM regra WHERE slug = ?", (r["slug"],)).fetchone()["proxima"]
    return {"ok": True, "slug": r["slug"], "nova": nova, "proxima": proxima}


def importar(con, itens, dia: date | None = None, por_dia: int = POR_DIA) -> dict:
    """Upsert de uma lista de regras e a primeira revisão espalhada (§13.3). Tudo ou nada."""
    if isinstance(itens, dict) and isinstance(itens.get("regras"), list):
        itens = itens["regras"]
    if not isinstance(itens, list):
        raise ValueError("o arquivo é uma lista [{slug, titulo, categoria, ensinada_em, explicacao_md}]")
    if por_dia < 1:
        raise ValueError("--por-dia é pelo menos 1")
    regras = [_validar(x, f"regra {i + 1}: ") for i, x in enumerate(itens)]
    repetidos = {r["slug"] for r in regras if sum(x["slug"] == r["slug"] for x in regras) > 1}
    if repetidos:
        raise ValueError(f"slug repetido no arquivo: {', '.join(sorted(repetidos))}")
    dia = dia or dominio.dia_de_estudo()
    try:
        novas = sum(_upsert(con, r, None) for r in regras)
        # As que ainda não têm agenda, as mais antigas primeiro: são as que ele mais esqueceu.
        sem_agenda = [x["id"] for x in con.execute(
            "SELECT id FROM regra WHERE proxima IS NULL ORDER BY ensinada_em IS NULL, ensinada_em, id")]
        datas = [(dia + timedelta(days=i // por_dia)).isoformat() for i in range(len(sem_agenda))]
        con.executemany("UPDATE regra SET proxima = ? WHERE id = ?", zip(datas, sem_agenda))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {"lidas": len(regras), "novas": novas, "atualizadas": len(regras) - novas,
            "agendadas": len(sem_agenda), "de": datas[0] if datas else None, "ate": datas[-1] if datas else None}


# ------------------------------------------------------------------ leitura

def listar(con, dia: date, vencidas: bool = True, limite: int = 10) -> list[dict]:
    """Para o MCP: enxuto, sem o texto da regra."""
    filtro, params = ("WHERE proxima <= ?", [dia.isoformat()]) if vencidas else ("", [])
    return db.linhas(con.execute(
        f"""SELECT slug, titulo, ensinada_em, proxima, intervalo, acertos, erros FROM regra {filtro}
            ORDER BY proxima IS NULL, proxima, ensinada_em, id LIMIT ?""", [*params, limite]))


def obter(con, slug: str) -> dict | None:
    r = con.execute("SELECT * FROM regra WHERE slug = ?", (slug,)).fetchone()
    return dict(r) if r else None


def resumo_vencidas(con, dia: date) -> dict:
    """O campo regras_vencidas do hoje(): quantas, e as 5 mais atrasadas."""
    (total,) = con.execute("SELECT COUNT(*) FROM regra WHERE proxima <= ?", (dia.isoformat(),)).fetchone()
    proximas = [r[0] for r in con.execute(
        "SELECT slug FROM regra WHERE proxima <= ? ORDER BY proxima, ensinada_em, id LIMIT 5", (dia.isoformat(),))]
    return {"total": total, "proximas": proximas}


def status(r: dict, dia: date) -> str:
    # `erros` conta só lacunas desde o esquema 5: um deslize não deixa a regra frágil
    if r["proxima"] and r["proxima"] <= dia.isoformat():
        return "vencida"
    return "fragil" if r["erros"] > r["acertos"] else "em_dia"


def caderno(con, dia: date) -> list[dict]:
    """GET /api/regras (§13.6): todas, com o texto e o status."""
    saida = []
    for r in db.linhas(con.execute(
            """SELECT slug, titulo, categoria, ensinada_em, explicacao_md, intervalo, proxima, acertos, erros,
                      deslizes, ultima_revisao, ultima_falha FROM regra
               ORDER BY proxima IS NULL, proxima, ensinada_em, id""")):
        r["dias"] = (date.fromisoformat(r["proxima"]) - dia).days if r["proxima"] else None
        r["status"] = status(r, dia)
        saida.append(r)
    return saida


# ------------------------------------------------------------------ linha de comando

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m japones.regras", description="Caderno de regras (DESIGN §13)")
    sub = ap.add_subparsers(dest="comando", required=True)
    imp = sub.add_parser("importar", help="upsert de um JSON [{slug, titulo, categoria, ensinada_em, explicacao_md}]")
    imp.add_argument("arquivo", type=Path)
    imp.add_argument("--por-dia", type=int, default=POR_DIA, help="primeiras revisões por dia (padrão 5)")
    a = ap.parse_args(argv)
    try:
        itens = json.loads(a.arquivo.read_text(encoding="utf-8"))
        con = db.conectar()
        try:
            r = importar(con, itens, por_dia=a.por_dia)
        finally:
            con.close()
    except (OSError, ValueError) as e:      # JSONDecodeError é ValueError
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
