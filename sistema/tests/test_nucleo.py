"""Domínio, leitura do diário e do currículo, e as ferramentas de escrita do MCP.
Rodam contra o diretório temporário do conftest."""
import os
from datetime import date, datetime
from pathlib import Path

import pytest

from japones import config, db, dominio
from japones.fontes import curriculo, diario


@pytest.fixture(autouse=True)
def banco_limpo():
    """Cada teste começa com banco e diário vazios."""
    for p in (config.BANCO, Path(str(config.BANCO) + "-wal"), Path(str(config.BANCO) + "-shm"), config.DIARIO):
        if p.exists():
            p.unlink()
    config.DIARIO.write_text("# Diário de Sessões\n")
    yield


def test_o_banco_de_teste_nao_e_o_real():
    assert ".local/share/japones" not in str(config.BANCO)
    assert config.DIARIO.parent == Path(os.environ["JAPONES_DADOS"])


# ------------------------------------------------------------------ domínio

def test_dia_vira_as_quatro():
    assert dominio.dia_de_estudo(datetime(2026, 10, 17, 1, 27)) == date(2026, 10, 16)
    assert dominio.dia_de_estudo(datetime(2026, 10, 17, 3, 59)) == date(2026, 10, 16)
    assert dominio.dia_de_estudo(datetime(2026, 10, 17, 4, 0)) == date(2026, 10, 17)


def test_streak_termina_hoje_ou_ontem():
    d = lambda dia: date(2026, 10, dia)
    datas = {d(1), d(2), d(3), d(5), d(6)}
    assert dominio.streak(datas, d(6)) == (2, 3)     # aula hoje
    assert dominio.streak(datas, d(7)) == (2, 3)     # hoje ainda sem aula: conta até ontem
    assert dominio.streak(datas, d(8)) == (0, 3)     # ontem sem aula: quebrou


def test_ano_pela_proximidade():
    assert dominio.ano_de(3, 1, date(2026, 12, 20)) == date(2027, 1, 3)
    assert dominio.ano_de(3, 8, date(2026, 8, 1)) == date(2026, 8, 3)


# ------------------------------------------------------------------ fontes de texto

DIARIO_EXEMPLO = """# Diário

## 2026-08-03 (dia 1 do plano) — completa
**Tempo:** 60 min · **Fase:** 0 · **Streak:** 1 dia
**Novo:** vogais

---

## 2026-10-15 (dia 67 do plano) — **sem sessão de mesa**
Quinta.

## 2026-10-16 (dia 68 do plano) — completa · **〜たことがあります**
**Tempo:** 60 min · **Início: 01:27 de sábado 17** · **Fase:** 1, semana 7 · **Streak:** 1

### Verificação: 3 de 5
### Produção: 2 de 5 limpas
**Amanhã:** sábado 17/10.
"""


def test_diario_estrutura_cada_entrada():
    e = diario.entradas(DIARIO_EXEMPLO)
    assert [x["tipo"] for x in e] == ["completa", "sem_mesa", "completa"]
    assert not e[0]["texto_md"].endswith("---")
    ult = e[-1]
    assert (ult["dia_plano"], ult["titulo"], ult["inicio"], ult["minutos"]) == (68, "〜たことがあります", "01:27", 60)
    assert (ult["fase"], ult["semana"]) == (1, 7)
    assert (ult["verif_ok"], ult["verif_total"], ult["prod_ok"], ult["prod_total"]) == (3, 5, 2, 5)
    assert e[0]["inicio"] is None   # formato antigo: sem horário, sem palpite


def test_diario_acrescenta_sem_reescrever():
    antes = config.DIARIO.read_text()
    diario.acrescentar("## 2026-10-17 (dia 69 do plano) — completa\nteste")
    depois = config.DIARIO.read_text()
    assert depois.startswith(antes)
    assert depois.rstrip().endswith("teste")
    assert "\n\n## 2026-10-17" in depois and "\n\n\n" not in depois   # uma linha em branco, não duas
    with pytest.raises(ValueError):
        diario.acrescentar("sem cabeçalho")


CURRICULO_EXEMPLO = """
| Dia | Data | Conteúdo |
|---|---|---|
| 67 | dom 11/10 | plano antigo |
| 68 | seg 12/10 | segunda |

| Dia | Data | Conteúdo |
|---|---|---|
| 67 | qua 14/10 | proibição |
| 69 | sáb 17/10 | に × で |
| 70 | dom 11/10 | replanejado |
"""


def test_curriculo_linha_mais_nova_vence():
    plano = curriculo.por_data(CURRICULO_EXEMPLO)
    assert plano["2026-10-11"]["conteudo"] == "replanejado"
    assert curriculo.do_dia(date(2026, 10, 17), CURRICULO_EXEMPLO)["dia_plano"] == 69


# ------------------------------------------------------------------ ferramentas MCP

def test_registrar_aula_grava_e_acrescenta_no_diario():
    from japones import mcp_server as m
    texto = "## 2026-10-17 (dia 69 do plano) — completa · **に × で**\n**Tempo:** 60 min"
    r = m.registrar_aula(data="2026-10-17", tipo="completa", texto_md=texto, titulo="に × で",
                         dia_plano=69, verif_ok=4, verif_total=5)
    assert r["ok"]
    assert config.DIARIO.read_text().rstrip().endswith("**Tempo:** 60 min")
    assert m.aulas(1)[0]["verif_ok"] == 4
    assert "erro" in m.registrar_aula(data="2026-10-17", tipo="completa", texto_md="## 2026-10-18 ...")
    assert "erro" in m.registrar_aula(data="2026-10-17", tipo="otima", texto_md=texto)


def test_registrar_trajeto_nao_apaga_o_que_existe():
    from japones import mcp_server as m
    m.registrar_trajeto(data="2026-10-16", anki_cartoes=236, anki_minutos=64.0)
    r = m.registrar_trajeto(data="2026-10-16", audio=True, audio_fonte="teppei", anki_cartoes=None)
    assert (r["anki_cartoes"], r["audio"], r["audio_fonte"]) == (236, 1, "teppei")


def test_erros_e_contagem_por_categoria():
    from japones import mcp_server as m
    hoje = dominio.dia_de_estudo().isoformat()
    m.registrar_erros(data=hoje, erros=[
        m.Erro(bloco="producao", categoria="particula:wo", escrito="日本を行った", correto="日本に行った"),
        m.Erro(bloco="producao", categoria="particula:wo", escrito="かばんをあります", correto="かばんにあります"),
        m.Erro(bloco="verificacao", categoria="forma-ta", escrito="いきた", correto="行った"),
    ])
    r = m.erros()
    assert r["por_categoria"] == {"particula:wo": 2, "forma-ta": 1}
    assert len(m.erros(categoria="particula")["erros"]) == 2


def test_hoje_sobrevive_com_as_fontes_fora(monkeypatch):
    from japones import mcp_server as m

    def cai(*a, **k):
        raise ConnectionError("sem rede")

    monkeypatch.setattr(m, "_resumo_trello", cai)
    monkeypatch.setattr(m, "_resumo_anki", cai)
    h = m.hoje()
    assert "erro" in h["trello"] and "erro" in h["anki"]
    assert h["dia_do_plano"] == 1 and h["ultima_aula"] is None


def test_nota_de_abertura_grava_e_apaga():
    from japones import mcp_server as m
    m.definir_nota("lembrete_abertura", "abrir com 3 rápidas")
    con = db.conectar()
    assert con.execute("SELECT valor FROM nota WHERE chave = 'lembrete_abertura'").fetchone()[0] == "abrir com 3 rápidas"
    m.definir_nota("lembrete_abertura", "")
    assert con.execute("SELECT COUNT(*) FROM nota").fetchone()[0] == 0
    con.close()


def test_backup_copia_o_banco_para_a_pasta_de_dados():
    from japones import mcp_server as m
    m.registrar_trajeto(data="2026-10-16", audio=True, anki_cartoes=1)
    r = m.backup()
    assert "estudo.db" in r["copiados"]
    assert (config.BACKUP / "estudo.db").exists()
    assert str(config.BACKUP).startswith(os.environ["JAPONES_DADOS"])
