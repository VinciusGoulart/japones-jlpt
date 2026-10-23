"""API HTTP do painel (DESIGN §10). Só escuta em 127.0.0.1.

    .venv/bin/python -m japones.api        # http://127.0.0.1:8787

Serve também o build do React (web/dist), com fallback de SPA: qualquer rota que
não seja /api devolve o index.html e o React Router resolve.
"""
from datetime import date, timedelta
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from japones import audio, db, dominio, exercicios, mcp_server, painel, regras
from japones.fontes import curriculo

DIST = Path(__file__).resolve().parents[1] / "web" / "dist"
HOST, PORTA = "127.0.0.1", 8787

app = FastAPI(title="Estudo de japonês", docs_url="/api/docs", openapi_url="/api/openapi.json")


def _con():
    return db.conectar()


@app.get("/api/hoje")
def hoje():
    return mcp_server.hoje()


@app.get("/api/aulas")
def aulas(ultimas: int = 30, busca: str | None = None):
    return mcp_server.aulas(ultimas=ultimas, busca=busca)


@app.get("/api/aulas/{data}")
def aula(data: str):
    r = mcp_server.aula(data)
    if not r:
        raise HTTPException(404, "nenhuma aula nesse dia")
    return r


@app.get("/api/erros")
def erros(dias: int = 30, categoria: str | None = None):
    return mcp_server.erros(categoria=categoria, dias=dias)


@app.get("/api/erros/painel")
def erros_painel(dias: int = 90):
    con = _con()
    try:
        return painel.erros_painel(con, dias)
    finally:
        con.close()


@app.get("/api/registro")
def registro(busca: str, limite: int = 20):
    return mcp_server.registro_antigo(busca=busca, limite=limite)


@app.get("/api/anki/painel")
def anki_painel():
    con = _con()
    try:
        return painel.anki_painel(con)
    finally:
        con.close()


@app.get("/api/kotoba/buscar")
def kotoba_buscar(q: str, limite: int = 20):
    return painel.kotoba_buscar(q, limite)


@app.get("/api/kotoba/kanji/{literal}")
def kotoba_kanji(literal: str):
    r = mcp_server.kanji(literal)
    if "erro" in r and len(r) == 1:
        raise HTTPException(404, r["erro"])
    return r


@app.get("/api/kotoba/historico")
def kotoba_historico(dias: int = 30):
    return painel.kotoba_historico(dias)


@app.get("/api/kotoba/listas")
def kotoba_listas():
    from japones.fontes import kotoba
    return mcp_server._seguro(kotoba.listas)


@app.get("/api/audio/{arquivo}")
def audio_mp3(arquivo: str):
    p = audio.caminho(arquivo.removesuffix(".mp3")) if arquivo.endswith(".mp3") else None
    if not p or not p.is_file():
        raise HTTPException(404, "áudio não encontrado")
    # o nome é o hash da fala: o mesmo nome é sempre o mesmo som, pode guardar em cache para sempre
    return FileResponse(p, media_type="audio/mpeg", headers={"Cache-Control": "max-age=31536000, immutable"})


@app.get("/api/calendario")
def calendario(de: str, ate: str):
    ini, fim = date.fromisoformat(de), date.fromisoformat(ate)
    if (fim - ini).days > 62:
        raise HTTPException(400, "intervalo máximo de 62 dias")
    con = _con()
    aulas_ = {}
    for r in con.execute("""SELECT data, tipo, titulo, dia_plano, verif_ok, verif_total, prod_ok, prod_total
                            FROM aula WHERE data BETWEEN ? AND ? ORDER BY id""", (de, ate)):
        aulas_.setdefault(r["data"], []).append({k: r[k] for k in r.keys() if k != "data"})
    trajeto = {r["data"]: {"anki_cartoes": r["anki_cartoes"], "anki_minutos": r["anki_minutos"], "audio": r["audio"]}
               for r in con.execute("SELECT * FROM trajeto WHERE data BETWEEN ? AND ?", (de, ate))}
    licoes = {}
    for r in con.execute("SELECT id, data, titulo, status FROM licao WHERE data BETWEEN ? AND ?", (de, ate)):
        licoes.setdefault(r["data"], []).append({"id": r["id"], "titulo": r["titulo"], "status": r["status"]})
    con.close()
    plano = curriculo.por_data()
    dias = []
    d = ini
    while d <= fim:
        k = d.isoformat()
        dias.append({"data": k, "aulas": aulas_.get(k, []), "trajeto": trajeto.get(k),
                     "plano": plano[k]["conteudo"] if k in plano else None, "licoes": licoes.get(k, [])})
        d += timedelta(days=1)

    def eventos():
        from japones.fontes import trello
        b = trello.board()
        return [{"nome": c["nome"], "vence": c["vence"], "url": c["url"], "concluido": c["concluido"], "lista": lista}
                for lista, cards in b["listas"].items() for c in cards
                if c["vence"] and de <= c["vence"] <= ate]
    return {"dias": dias, "eventos_trello": mcp_server._seguro(eventos)}


@app.get("/api/licoes")
def licoes(ultimas: int = 20):
    con = _con()
    r = exercicios.resumo_licoes(con, ultimas)
    con.close()
    return r


@app.get("/api/licoes/atual")
def licao_atual():
    con = _con()
    lid = exercicios.licao_atual_id(con)
    r = exercicios.licao_renderizada(con, lid) if lid else None
    con.close()
    if not r:
        raise HTTPException(404, "nenhuma lição criada ainda")
    return r


@app.get("/api/licoes/{licao_id}")
def licao(licao_id: int):
    con = _con()
    r = exercicios.licao_renderizada(con, licao_id)
    con.close()
    if not r:
        raise HTTPException(404, "lição não encontrada")
    return r


@app.post("/api/exercicios/{exercicio_id}/resposta")
def responder(exercicio_id: int, resposta: dict = Body(...), tempo_ms: int | None = Body(None)):
    con = _con()
    try:
        return exercicios.responder(con, exercicio_id, resposta, tempo_ms)
    except KeyError:
        raise HTTPException(404, "exercício não encontrado")
    except ValueError as e:     # o explicacao não tem resposta (§9.2)
        raise HTTPException(400, str(e))
    finally:
        con.close()


@app.post("/api/exercicios/{exercicio_id}/desistir")
def desistir(exercicio_id: int):
    """"Ver a resposta" com a dica pendente (§9.6): grava a desistência (lacuna) e devolve a correção da 1ª."""
    con = _con()
    try:
        return exercicios.desistir(con, exercicio_id)
    except KeyError:
        raise HTTPException(404, "exercício não encontrado")
    except ValueError as e:     # sem dica esperando: nada a desistir
        raise HTTPException(409, str(e))
    finally:
        con.close()


@app.get("/api/regras")
def listar_regras():
    """O caderno de regras (§13.6): todas, com o texto, a agenda e o status."""
    con = _con()
    try:
        return regras.caderno(con, dominio.dia_de_estudo())
    finally:
        con.close()


# ------------------------------------------------------------------ o React

if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/{caminho:path}", include_in_schema=False)
def spa(caminho: str):
    if caminho.startswith("api/"):
        raise HTTPException(404)
    arquivo = DIST / caminho
    if caminho and arquivo.is_file() and DIST in arquivo.resolve().parents:
        return FileResponse(arquivo)
    if (DIST / "index.html").exists():
        return FileResponse(DIST / "index.html")
    return HTMLResponse("<p>O build do painel ainda não existe: rode <code>npm run build</code> em "
                        "<code>sistema/web</code>. A API está em <a href='/api/docs'>/api/docs</a>.</p>")


def main():
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORTA, log_level="warning")


if __name__ == "__main__":
    main()
