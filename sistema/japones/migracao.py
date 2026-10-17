"""Importação do histórico para o estudo.db.

Pode rodar de novo sem duplicar: apaga e refaz só o que ela mesma importou
(origem = 'migracao'), e pula as aulas que já entraram pelo MCP.

    .venv/bin/python -m japones.migracao            # tudo
    .venv/bin/python -m japones.migracao --sem-rede # sem Trello (áudio fica vazio)
"""
import json
import re
import sys
from datetime import date

from japones import config, db
from japones.dominio import ano_de
from japones.fontes import anki, diario, trello

# Padrões abertos em 17/10/2026, semeados à mão a partir do topo de pontos_fracos.
# Daqui para frente o ciclo é pelo MCP (abrir_padrao / resolver_padrao).
PADROES_INICIAIS = [
    ("particula:posicao", "2026-10-13",
     "Partícula escolhida pela POSIÇÃO na frase, não pelo papel: com o gato fixo na frente saiu "
     "猫に部屋がいます (に antes, が depois). Modelo declarado por ele em 16/10: 'に é lugar genérico, "
     "で é lugar específico ou ferramenta'. Regra certa: decide o VERBO (estar/ir → に; fazer → で)."),
    ("particula:wo", "2026-10-16",
     "を como partícula padrão antes do verbo quando o verbo é de ESTAR ou IR: 日本を行った, "
     "かばんをあります. Nas ações ele acerta o で."),
    ("forma-te", "2026-10-05",
     "Tabela て/た por terminação não automatizada: んて sem dakuten (3x), 買うて, いきた (forma た "
     "montada sobre a forma ます), 撮る esquecido. Ele pediu a tabela em 16/10."),
    ("adjetivo:familia", "2026-10-09",
     "A família da palavra decide o conector e ele usa o maquinário da família errada: 難しいで, "
     "たいくって, ながいで; かった×だった no casual."),
    ("iru-aru", "2026-10-08",
     "いる × ある trocados (5ª vez em 09/10). Em 16/10 ある saiu certo para a carteira."),
    ("kana:vogal-longa", "2026-10-13",
     "Vogal longa e troca あ/お: もお em vez de もう (16/10); おんしん em vez de あんしん (あ→お, 3ª vez)."),
]


def _inicio_do_estado(horarios: dict) -> dict:
    """'2026-10-13': '23:09 (ter; ...)' -> '23:09'."""
    saida = {}
    for d, txt in horarios.items():
        m = re.match(r"\s*(\d{1,2}):(\d{2})", txt)
        if m:
            saida[d] = f"{int(m.group(1)):02d}:{m.group(2)}"
    return saida


def migrar_aulas(con) -> int:
    estado = json.loads(config.ESTADO.read_text())
    inicios = _inicio_do_estado(estado.get("mesa", {}).get("horarios_inicio", {}))
    via_mcp = {(r["data"], r["tipo"]) for r in con.execute("SELECT data, tipo FROM aula WHERE origem = 'mcp'")}
    con.execute("DELETE FROM aula WHERE origem = 'migracao'")
    n = 0
    for e in diario.entradas():
        if (e["data"], e["tipo"]) in via_mcp:
            continue
        if not e["inicio"] and e["tipo"] != "sem_mesa":
            e["inicio"] = inicios.get(e["data"])
        con.execute("""INSERT INTO aula (data, dia_plano, tipo, titulo, fase, semana, inicio, minutos,
                         verif_ok, verif_total, prod_ok, prod_total, texto_md, origem)
                       VALUES (:data, :dia_plano, :tipo, :titulo, :fase, :semana, :inicio, :minutos,
                         :verif_ok, :verif_total, :prod_ok, :prod_total, :texto_md, 'migracao')""", e)
        n += 1
    return n


def migrar_trajeto_anki(con) -> int:
    dias = anki.historico_por_dia()
    for d in dias:
        con.execute("""INSERT INTO trajeto (data, anki_cartoes, anki_minutos) VALUES (?, ?, ?)
                       ON CONFLICT(data) DO UPDATE SET anki_cartoes = excluded.anki_cartoes,
                                                       anki_minutos = excluded.anki_minutos""",
                    (d["data"], d["cartoes"], d["minutos"]))
    return len(dias)


def migrar_audio_trello(con) -> int:
    """Os checklists '🎧 Semana N' do board: item marcado = áudio feito naquele dia."""
    b = trello.board()
    n = 0
    for cards in b["listas"].values():
        for c in cards:
            if not c["nome"].startswith("🎧"):
                continue
            # os itens feitos não vêm em 'faltam'; reconstruímos pelo nome da semana
            m = re.search(r"\((\d{2})/(\d{2}) a (\d{2})/(\d{2})\)", c["nome"])
            if not m:
                continue
            ini = ano_de(int(m.group(1)), int(m.group(2)), config.INICIO_PLANO)
            for cl in c["checklists"]:
                faltam = set(cl["faltam"])
                for k in range(7):
                    d = date.fromordinal(ini.toordinal() + k)
                    rotulo = f"{['Seg','Ter','Qua','Qui','Sex','Sab','Dom'][d.weekday()]} {d:%d/%m}"
                    if rotulo in faltam or d > date.today():
                        continue
                    con.execute("""INSERT INTO trajeto (data, audio, audio_fonte) VALUES (?, 1, 'trello')
                                   ON CONFLICT(data) DO UPDATE SET audio = 1,
                                     audio_fonte = COALESCE(trajeto.audio_fonte, 'trello')""",
                                (d.isoformat(),))
                    n += 1
    return n


def migrar_registro(con) -> int:
    estado = json.loads(config.ESTADO.read_text())
    con.execute("DELETE FROM registro WHERE origem IN ('pontos_fracos', 'vigiar')")
    n = 0
    for origem in ("pontos_fracos", "vigiar"):
        for texto in estado.get(origem, []):
            texto = texto if isinstance(texto, str) else json.dumps(texto, ensure_ascii=False)
            # a data vem no começo, mas nem sempre na 1ª posição ("dia 5 (08/08) —", "PADRAO 13/09:")
            m = re.search(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)", texto[:60])
            data = None
            if m:
                try:
                    data = ano_de(int(m.group(1)), int(m.group(2)), config.INICIO_PLANO).isoformat()
                except ValueError:
                    pass
            con.execute("INSERT INTO registro (data, texto, origem) VALUES (?, ?, ?)", (data, texto, origem))
            n += 1
    return n


def migrar_notas_e_padroes(con) -> tuple[int, int]:
    estado = json.loads(config.ESTADO.read_text())
    notas = 0
    if estado.get("lembrete_abertura"):
        notas += con.execute("INSERT OR IGNORE INTO nota (chave, valor) VALUES ('lembrete_abertura', ?)",
                             (estado["lembrete_abertura"],)).rowcount
    padroes = 0
    if not con.execute("SELECT 1 FROM padrao LIMIT 1").fetchone():
        for cat, desde, desc in PADROES_INICIAIS:
            con.execute("INSERT INTO padrao (categoria, descricao, aberto_em) VALUES (?, ?, ?)", (cat, desc, desde))
            padroes += 1
    return notas, padroes


def migrar(rede: bool = True) -> dict:
    con = db.conectar()
    rel = {"aulas": migrar_aulas(con)}
    try:
        rel["trajeto_anki_dias"] = migrar_trajeto_anki(con)
    except anki.AnkiIndisponivel as e:
        rel["trajeto_anki_dias"] = f"pulado: {e}"
    if rede:
        try:
            rel["audio_dias"] = migrar_audio_trello(con)
        except trello.TrelloIndisponivel as e:
            rel["audio_dias"] = f"pulado: {e}"
    rel["registro"] = migrar_registro(con)
    rel["notas"], rel["padroes"] = migrar_notas_e_padroes(con)
    con.commit()
    con.close()
    return rel


if __name__ == "__main__":
    print(json.dumps(migrar(rede="--sem-rede" not in sys.argv), ensure_ascii=False, indent=2))
