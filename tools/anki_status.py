#!/usr/bin/env python3
"""
Le a colecao do Anki e imprime o estado real do estudo.

Existe porque durante os 10 primeiros dias a unica fonte sobre o trajeto era o que
ele lembrava de contar, e a metrica mais importante (minutos) faltou seis dias
seguidos. O primeiro numero real so apareceu por acaso, num print mandado por
outro motivo. Isto tira o relato do meio.

FONTE (desde 28/08): a colecao do Anki DESKTOP (~/.local/share/Anki2/), que o
AnkiWeb mantem sincronizada com o AnkiDroid. Sempre lida de uma COPIA -- nunca
o arquivo vivo, que o Anki aberto pode estar usando. O export manual .colpkg
em ~/.local/share/japones/ continua funcionando como fallback e como override
por argumento.

SO LE. Nunca escreve na colecao -- o arquivo do Anki e dele, e um bug meu aqui
custaria historico de revisao que nao se recupera.

Uso:  python3 tools/anki_status.py [caminho]
      sem argumento: colecao do desktop; sem desktop: export mais recente

Se a leitura estiver velha: abrir o Anki no PC (sincroniza ao abrir/fechar) ou
sincronizar o AnkiDroid primeiro se o estudo acabou de acontecer no celular.
"""
import glob
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile

PASTA = os.path.expanduser("~/.local/share/japones")
DESKTOP_GLOB = os.path.expanduser("~/.local/share/Anki2/*/collection.anki2")
ROLLOVER_H = 4  # o "dia" do Anki vira as 4h, nao a meia-noite


def achar_fonte(caminho=None):
    """Devolve (caminho, rotulo, mtime, origem). origem: 'desktop' ou 'export'.

    Para o desktop, o caminho devolvido ja e uma COPIA em tmp: o original nunca
    e aberto (lock do Anki em uso, e seguranca -- copia nao tem como escrever
    no arquivo dele nem deixar -wal/-shm para tras).
    """
    if caminho:
        return caminho, os.path.basename(caminho), os.path.getmtime(caminho), "export"

    perfis = sorted(glob.glob(DESKTOP_GLOB), key=os.path.getmtime, reverse=True)
    if perfis:
        original = perfis[0]
        copia = os.path.join(tempfile.mkdtemp(), "collection.anki2")
        shutil.copy2(original, copia)
        # Com o Anki ABERTO, as mudancas recentes vivem no -wal (write-ahead log
        # do SQLite): copiar so o arquivo principal devolve um retrato VELHO —
        # em 30/08 isso escondeu uma importacao de 371 notas. Sidecars vem junto.
        for sufixo in ("-wal", "-shm"):
            if os.path.exists(original + sufixo):
                shutil.copy2(original + sufixo, copia + sufixo)
        perfil = os.path.basename(os.path.dirname(original))
        # frescor = o mais novo entre o arquivo principal e o WAL: com o Anki
        # aberto quem recebe as escritas e o WAL, e olhar so o principal
        # acusava 'sem sync' com dados de hoje na tela
        mtime = max(os.path.getmtime(p) for p in [original, original + "-wal"]
                    if os.path.exists(p))
        return copia, f"desktop · perfil '{perfil}'", mtime, "desktop"

    achados = sorted(glob.glob(os.path.join(PASTA, "*.colpkg")) +
                     glob.glob(os.path.join(PASTA, "*.apkg")),
                     key=os.path.getmtime, reverse=True)
    if not achados:
        print(f"Nem colecao do desktop ({DESKTOP_GLOB}), nem export em {PASTA}.\n\n"
              f"Caminho preferido: instalar o Anki desktop e sincronizar com o AnkiWeb.\n"
              f"Fallback: no AnkiDroid, menu (⋮) > Exportar colecao > mover para {PASTA}.\n",
              file=sys.stderr)
        sys.exit(2)
    return achados[0], os.path.basename(achados[0]), os.path.getmtime(achados[0]), "export"


def abrir(caminho):
    """Extrai o SQLite do pacote.

    ORDEM IMPORTA. O Anki 2.1.50+ grava a colecao real em collection.anki21b,
    comprimida com zstd, e deixa um collection.anki2 de ~50 KB como placeholder
    vazio para versoes antigas nao quebrarem. Ler o .anki2 primeiro faz o script
    reportar "Default: 1 cartao" e nenhum historico -- foi o que aconteceu em
    22/08 com o export de 20/08.
    """
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()

        if "collection.anki21b" in nomes:
            z.extract("collection.anki21b", tmp)
            comprimido = os.path.join(tmp, "collection.anki21b")
            destino = os.path.join(tmp, "collection.anki2")
            r = subprocess.run(["zstd", "-d", "-q", "-f", comprimido, "-o", destino],
                               capture_output=True, text=True)
            if r.returncode == 0 and os.path.exists(destino):
                return destino
            print(f"falhou ao descomprimir com zstd: {r.stderr.strip()}\n"
                  f"instale com: sudo apt install zstd", file=sys.stderr)
            sys.exit(3)

        for alvo in ("collection.anki21", "collection.anki2"):
            if alvo in nomes:
                z.extract(alvo, tmp)
                return os.path.join(tmp, alvo)

    print(f"nao achei nenhuma colecao dentro de {caminho}", file=sys.stderr)
    sys.exit(3)


def nomes_de_deck(con):
    """Schema 18 tem tabela 'decks'; schema 11 guarda tudo num JSON em col."""
    try:
        return {i: n.replace("\x1f", "::") for i, n in
                con.execute("SELECT id, name FROM decks")}
    except sqlite3.OperationalError:
        (bruto,) = con.execute("SELECT decks FROM col").fetchone()
        return {int(k): v["name"] for k, v in json.loads(bruto).items()}


def dia_anki(crt):
    """Quantos dias 'do Anki' se passaram desde a criacao da colecao."""
    return int((time.time() - crt) // 86400)


def inicio_do_dia_ms(dias_atras=0):
    t = time.localtime()
    meia = time.mktime((t.tm_year, t.tm_mon, t.tm_mday, ROLLOVER_H, 0, 0, 0, 0, -1))
    if time.time() < meia:      # antes das 4h ainda e "ontem" para o Anki
        meia -= 86400
    return int((meia - dias_atras * 86400) * 1000)


def barra(n, total, largura=24):
    if not total:
        return ""
    return "█" * max(0, min(largura, round(n / total * largura)))


def main():
    caminho, rotulo, mtime, origem = achar_fonte(sys.argv[1] if len(sys.argv) > 1 else None)
    db = caminho if caminho.endswith(".anki2") else abrir(caminho)
    # A copia do desktop abre em leitura-escrita porque o SQLite precisa
    # aplicar o WAL copiado (e a copia e descartavel); qualquer outra fonte
    # abre read-only por seguranca.
    if origem == "desktop":
        con = sqlite3.connect(db)
    else:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    (crt,) = con.execute("SELECT crt FROM col").fetchone()
    hoje = dia_anki(crt)
    decks = nomes_de_deck(con)

    print("=" * 66)
    print(f"ANKI — {rotulo}")
    idade = (time.time() - mtime) / 86400
    if origem == "desktop":
        print(f"ultima escrita ha {idade:.1f} dia(s)" +
              ("   ⚠️  sem sync recente" if idade > 1.5 else "   🟢 via AnkiWeb"))
        if idade > 1.5:
            print("\n   ⚠️  A COLECAO DO DESKTOP NAO SINCRONIZA HA MAIS DE UM DIA:")
            print("       abra o Anki no PC (ele sincroniza ao abrir/fechar). Se o estudo")
            print("       acabou de acontecer no celular, sincronize o AnkiDroid primeiro.")
    else:
        print(f"export de {idade:.1f} dia(s) atras" +
              ("   ⚠️  desatualizado" if idade > 3 else ""))
        if idade > 3:
            print("\n   ⚠️  COM EXPORT VELHO, DOIS NUMEROS ABAIXO MENTEM:")
            print("       · FILA DE ATRASADOS conta como se nada tivesse sido estudado desde o export")
            print("       · ULTIMOS 7 DIAS fica zerado porque o historico do arquivo termina na data dele")
            print("       Nao use nenhum dos dois para decidir ritmo. Exporte de novo.")
    print("=" * 66)

    # ---- por baralho
    print("\n▸ BARALHOS")
    linhas = con.execute("""
        SELECT did,
               COUNT(*),
               SUM(queue = 0),
               SUM(queue = 2 AND due <= ?),
               SUM(queue IN (1, 3)),
               SUM(queue = -1)
        FROM cards GROUP BY did ORDER BY COUNT(*) DESC""", (hoje,)).fetchall()
    print(f"   {'baralho':38s} {'total':>6} {'novos':>6} {'devidos':>8} {'aprend':>7} {'susp':>5}")
    for did, tot, novos, dev, apr, susp in linhas:
        nome = decks.get(did, f"?{did}")[-38:]
        print(f"   {nome:38s} {tot:>6} {novos or 0:>6} {dev or 0:>8} {apr or 0:>7} {susp or 0:>5}")

    # ---- fila de atrasados (o gatilho do plano: > 200 zera os novos)
    (atrasados,) = con.execute(
        "SELECT COUNT(*) FROM cards WHERE queue = 2 AND due < ?", (hoje,)).fetchone()
    print(f"\n▸ FILA DE ATRASADOS: {atrasados}", end="")
    if atrasados > 200:
        print("   🔴 ACIMA DE 200 — zerar cartoes novos ate normalizar")
    elif atrasados > 100:
        print("   🟡 crescendo, nao aumentar o ritmo de novos")
    else:
        print("   🟢 sob controle")

    # ---- atividade dos ultimos 7 dias
    print("\n▸ ULTIMOS 7 DIAS")
    print(f"   {'dia':>5} {'cartoes':>8} {'minutos':>8}")
    total_min = total_cards = 0
    for d in range(6, -1, -1):
        ini, fim = inicio_do_dia_ms(d), inicio_do_dia_ms(d - 1)
        n, ms = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(time),0) FROM revlog WHERE id >= ? AND id < ?",
            (ini, fim)).fetchone()
        mins = ms / 60000
        total_cards += n
        total_min += mins
        rotulo = "hoje" if d == 0 else f"-{d}d"
        print(f"   {rotulo:>5} {n:>8} {mins:>7.0f}  {barra(mins, 60)}")
    print(f"   {'soma':>5} {total_cards:>8} {total_min:>7.0f}   "
          f"(media {total_min/7:.0f} min/dia)")

    # ---- retencao real
    ini = inicio_do_dia_ms(30)
    linha = con.execute(
        "SELECT COUNT(*), SUM(ease > 1) FROM revlog WHERE id >= ? AND type = 1", (ini,)
    ).fetchone()
    if linha and linha[0]:
        tot, ok = linha[0], linha[1] or 0
        print(f"\n▸ RETENCAO (30 dias, so revisoes): {ok}/{tot} = {ok/tot*100:.0f}%", end="")
        print("   — alvo saudavel: 85-90%" if ok/tot < 0.85 or ok/tot > 0.95 else "   🟢")

    # ---- cartoes problematicos: alimentam pontos_fracos no estado.json
    print("\n▸ CARTOES QUE MAIS TRAVAM (lapses ≥ 3)")
    piores = con.execute("""
        SELECT n.flds, c.lapses, c.did FROM cards c JOIN notes n ON n.id = c.nid
        WHERE c.lapses >= 3 ORDER BY c.lapses DESC LIMIT 12""").fetchall()
    if not piores:
        print("   (nenhum — ainda nao ha historico suficiente)")
    for flds, lapses, did in piores:
        frente = flds.split("\x1f")[0][:44]
        print(f"   {lapses:>3}x  {frente:46s} {decks.get(did,'')[-22:]}")

    con.close()
    print()


if __name__ == "__main__":
    main()
