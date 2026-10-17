"""Consultas das telas da Fase 3 (DESIGN §12): Erros, Anki e Kotoba.

São agregados para gráfico, feitos para o navegador, não para o tutor: o MCP
continua com as respostas enxutas dele. A mesma regra do MCP vale aqui: fonte
fora do ar vira {"erro": ...} no campo dela e o resto da tela aparece.
"""
from datetime import date, datetime, timedelta

from japones import config, db, dominio
from japones.mcp_server import _seguro


def _segunda(dia: str) -> str:
    d = date.fromisoformat(dia)
    return (d - timedelta(days=d.weekday())).isoformat()


def _grupo(categoria: str) -> str:
    return categoria.split(":", 1)[0]


# ------------------------------------------------------------------ erros (§12.1)

def erros_painel(con, dias: int = 90) -> dict:
    desde = (dominio.dia_de_estudo() - timedelta(days=dias)).isoformat()
    por_categoria = [{"categoria": c, "grupo": _grupo(c), "n": n, "ultimo": u} for c, n, u in con.execute(
        "SELECT categoria, COUNT(*), MAX(data) FROM erro WHERE data >= ? GROUP BY categoria "
        "ORDER BY COUNT(*) DESC, MAX(data) DESC", (desde,))]

    semanas: dict[tuple[str, str], int] = {}
    for dia, categoria, n in con.execute(
            "SELECT data, categoria, COUNT(*) FROM erro WHERE data >= ? GROUP BY data, categoria", (desde,)):
        k = (_segunda(dia), _grupo(categoria))
        semanas[k] = semanas.get(k, 0) + n
    por_semana = [{"semana": s, "grupo": g, "n": n} for (s, g), n in sorted(semanas.items())]

    por_bloco = dict(con.execute("SELECT bloco, COUNT(*) FROM erro WHERE data >= ? GROUP BY bloco", (desde,)).fetchall())

    # só a PRIMEIRA resposta de cada exercício conta (DESIGN §9.2)
    tipos = []
    for tipo, total, certos, errados, revisar in con.execute("""
            SELECT e.tipo, COUNT(*), SUM(r.veredito = 'certo'), SUM(r.veredito = 'errado'), SUM(r.veredito = 'revisar')
            FROM exercicio e JOIN licao l ON l.id = e.licao_id
            JOIN resposta r ON r.id = (SELECT MIN(id) FROM resposta WHERE exercicio_id = e.id)
            WHERE l.data >= ? GROUP BY e.tipo ORDER BY e.tipo""", (desde,)):
        fechados = (certos or 0) + (errados or 0)
        tipos.append({"tipo": tipo, "respondidos": total, "certos": certos or 0, "errados": errados or 0,
                      "revisar": revisar or 0, "taxa_erro": round((errados or 0) / fechados, 3) if fechados else None})

    padroes = {s + "s": db.linhas(con.execute(
        "SELECT * FROM padrao WHERE status = ? ORDER BY COALESCE(resolvido_em, aberto_em) DESC", (s,)))
        for s in ("aberto", "resolvido")}
    (primeiro,) = con.execute("SELECT MIN(data) FROM erro").fetchone()
    return {"desde": desde, "primeiro_erro": primeiro, "total": sum(c["n"] for c in por_categoria),
            "por_categoria": por_categoria,
            "por_semana": por_semana, "por_bloco": por_bloco, "tipos_exercicio": tipos, "padroes": padroes}


# ------------------------------------------------------------------ anki (§12.2)

def anki_painel(con) -> dict:
    from japones.fontes import anki

    status = _seguro(anki.status)
    graficos = _seguro(anki.graficos)
    ao_vivo = _seguro(anki.historico_por_dia)
    gravado = {r["data"]: r for r in con.execute(
        "SELECT data, anki_cartoes, anki_minutos, audio FROM trajeto WHERE data >= ?", (config.INICIO_PLANO.isoformat(),))}
    # Anki fora do ar: os números que o registrar_trajeto gravou dia a dia
    revisoes = ({r["data"]: (r["cartoes"], r["minutos"]) for r in ao_vivo} if isinstance(ao_vivo, list)
                else {d: (r["anki_cartoes"], r["anki_minutos"]) for d, r in gravado.items()})

    por_dia, d, hoje = [], config.INICIO_PLANO, dominio.dia_de_estudo()
    while d <= hoje:
        k = d.isoformat()
        cartoes, minutos = revisoes.get(k, (0, 0))
        por_dia.append({"data": k, "cartoes": cartoes or 0, "minutos": minutos or 0,
                        "audio": gravado[k]["audio"] if k in gravado else None})
        d += timedelta(days=1)
    return {"status": status, "graficos": graficos, "por_dia": por_dia,
            **({"fonte_por_dia": "banco (o Anki não abriu)"} if not isinstance(ao_vivo, list) else {})}


# ------------------------------------------------------------------ kotoba (§12.4)

def _indice_anki() -> dict | None:
    from japones.fontes import anki
    r = _seguro(anki.indice_de_cartoes)
    return None if "erro" in r else r


def _tem(indice: dict | None, formas: tuple, leitura: str | None) -> bool | None:
    """A grafia casa com qualquer campo; a leitura, só com frente de nota escrita em kana (homófonos)."""
    if indice is None:
        return None
    return any(f and f in indice["campos"] for f in formas) or bool(leitura and leitura in indice["frentes_kana"])


def kotoba_buscar(q: str, limite: int = 20) -> dict:
    from japones.fontes import kotoba

    def buscar():
        resultados = kotoba.buscar(q, limite, detalhado=True)
        indice = _indice_anki()
        for r in resultados:
            r["tem_cartao"] = _tem(indice, (r.get("palavra"), r.get("grafia_kanji")), r.get("leitura"))
        return {"resultados": resultados}
    return _seguro(buscar)


def _leitura(kotoba, palavra: str, ent_seq: int | None) -> str | None:
    """A leitura do verbete que ele abriu: o histórico só guarda o rótulo ('持つ · segurar')."""
    if not ent_seq:
        return None
    for r in kotoba.buscar(palavra, 5):
        if r.get("ent_seq") == ent_seq:
            return r.get("leitura")
    return None


def kotoba_historico(dias: int = 30, ate: date | None = None) -> dict:
    """As consultas dos `dias` dias de estudo que terminam em `ate` (padrão: hoje)."""
    from japones.fontes import kotoba

    def ler():
        hoje = ate or dominio.dia_de_estudo()
        ini, _ = dominio.intervalo_do_dia(hoje - timedelta(days=dias - 1))
        _, fim = dominio.intervalo_do_dia(hoje)
        consultas = kotoba.historico(desde=ini, ate=fim, limite=1000)
        indice = _indice_anki()
        por_dia: dict[str, list] = {}
        candidatas: dict[int, dict] = {}
        leituras: dict[int, str | None] = {}
        for c in consultas:
            dia = dominio.dia_de_estudo(datetime.fromisoformat(c["quando"])).isoformat()
            palavra = c["rotulo"].split(" · ", 1)[0] if c["tipo"] == "entry" and c["rotulo"] else None
            item = {k: c[k] for k in ("tipo", "rotulo", "consulta", "kanji", "quando", "ent_seq")}
            item["palavra"] = palavra
            if palavra:
                if c["ent_seq"] not in leituras:
                    leituras[c["ent_seq"]] = _leitura(kotoba, palavra, c["ent_seq"])
                item["leitura"] = leituras[c["ent_seq"]]
                item["tem_cartao"] = _tem(indice, (palavra,), item["leitura"])
                if item["tem_cartao"] is False:
                    cand = candidatas.setdefault(c["ent_seq"], {"palavra": palavra, "leitura": item["leitura"],
                                                                "rotulo": c["rotulo"], "vezes": 0, "ultima": dia})
                    cand["vezes"] += 1
            por_dia.setdefault(dia, []).append(item)
        return {"dias": [{"data": d, "consultas": v} for d, v in sorted(por_dia.items(), reverse=True)],
                # mais consultada primeiro; no empate, a mais recente
                "sem_cartao": sorted(sorted(candidatas.values(), key=lambda x: x["ultima"], reverse=True),
                                     key=lambda x: -x["vezes"]),
                **({"aviso": "o Anki não abriu: não dá para saber o que já tem cartão"} if indice is None else {})}
    return _seguro(ler)
