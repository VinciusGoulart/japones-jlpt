#!/usr/bin/env python3
"""
Gera o deck de kana da Fase 0 em TSV importavel pelo Anki (sem dependencias).

As tags seguem a sequencia de plano/curriculo.md, entao da para liberar uma
linha por dia no Anki filtrando por tag em vez de despejar 92 cartoes no dia 1.

Uso:  python3 tools/gerar_kana_tsv.py
Saida: anki/kana-fase0.tsv
"""
import os

# (linha, [(caractere, leitura), ...])
HIRAGANA = [
    ("a",  [("あ","a"),("い","i"),("う","u"),("え","e"),("お","o")]),
    ("ka", [("か","ka"),("き","ki"),("く","ku"),("け","ke"),("こ","ko")]),
    ("sa", [("さ","sa"),("し","shi"),("す","su"),("せ","se"),("そ","so")]),
    ("ta", [("た","ta"),("ち","chi"),("つ","tsu"),("て","te"),("と","to")]),
    ("na", [("な","na"),("に","ni"),("ぬ","nu"),("ね","ne"),("の","no")]),
    ("ha", [("は","ha"),("ひ","hi"),("ふ","fu"),("へ","he"),("ほ","ho")]),
    ("ma", [("ま","ma"),("み","mi"),("む","mu"),("め","me"),("も","mo")]),
    ("ya", [("や","ya"),("ゆ","yu"),("よ","yo")]),
    ("ra", [("ら","ra"),("り","ri"),("る","ru"),("れ","re"),("ろ","ro")]),
    ("wa", [("わ","wa"),("を","wo"),("ん","n")]),
]

KATAKANA = [
    ("a",  [("ア","a"),("イ","i"),("ウ","u"),("エ","e"),("オ","o")]),
    ("ka", [("カ","ka"),("キ","ki"),("ク","ku"),("ケ","ke"),("コ","ko")]),
    ("sa", [("サ","sa"),("シ","shi"),("ス","su"),("セ","se"),("ソ","so")]),
    ("ta", [("タ","ta"),("チ","chi"),("ツ","tsu"),("テ","te"),("ト","to")]),
    ("na", [("ナ","na"),("ニ","ni"),("ヌ","nu"),("ネ","ne"),("ノ","no")]),
    ("ha", [("ハ","ha"),("ヒ","hi"),("フ","fu"),("ヘ","he"),("ホ","ho")]),
    ("ma", [("マ","ma"),("ミ","mi"),("ム","mu"),("メ","me"),("モ","mo")]),
    ("ya", [("ヤ","ya"),("ユ","yu"),("ヨ","yo")]),
    ("ra", [("ラ","ra"),("リ","ri"),("ル","ru"),("レ","re"),("ロ","ro")]),
    ("wa", [("ワ","wa"),("ヲ","wo"),("ン","n")]),
]

# Dakuten e handakuten (dia 12 do curriculo)
DAKUTEN_H = [
    ("ga", [("が","ga"),("ぎ","gi"),("ぐ","gu"),("げ","ge"),("ご","go")]),
    ("za", [("ざ","za"),("じ","ji"),("ず","zu"),("ぜ","ze"),("ぞ","zo")]),
    ("da", [("だ","da"),("ぢ","ji"),("づ","zu"),("で","de"),("ど","do")]),
    ("ba", [("ば","ba"),("び","bi"),("ぶ","bu"),("べ","be"),("ぼ","bo")]),
    ("pa", [("ぱ","pa"),("ぴ","pi"),("ぷ","pu"),("ぺ","pe"),("ぽ","po")]),
]

# Yoon: combinacoes com や/ゆ/よ pequenos (dia 13)
YOON_BASES = [("き","ky"),("し","sh"),("ち","ch"),("に","ny"),("ひ","hy"),
              ("み","my"),("り","ry"),("ぎ","gy"),("じ","j"),("び","by"),("ぴ","py")]
YOON_SUFIXOS = [("ゃ","a"),("ゅ","u"),("ょ","o")]

# Pares visualmente confundiveis: recebem tag extra para revisao dirigida
CONFUNDIVEIS = {"シ","ツ","ソ","ン","ク","ワ","ス","ヌ","ネ","レ","ル","ロ","は","ほ","ま","わ","ね","れ"}


def linhas_do_bloco(blocos, silabario, prefixo_tag):
    saida = []
    for nome_linha, caracteres in blocos:
        for kana, leitura in caracteres:
            tags = [silabario, f"{prefixo_tag}-{nome_linha}"]
            if kana in CONFUNDIVEIS:
                tags.append("confundivel")
            saida.append((kana, leitura, " ".join(tags)))
    return saida


def gerar_yoon():
    saida = []
    for base, consoante in YOON_BASES:
        for pequeno, vogal in YOON_SUFIXOS:
            kana = base + pequeno
            # shi/chi/ji perdem a vogal 'i' na combinacao: しゃ = sha, nao shia
            leitura = consoante + vogal
            saida.append((kana, leitura, "hiragana yoon"))
    return saida


def main():
    registros = []
    registros += linhas_do_bloco(HIRAGANA, "hiragana", "hira")
    registros += linhas_do_bloco(KATAKANA, "katakana", "kata")
    registros += linhas_do_bloco(DAKUTEN_H, "hiragana", "dakuten")
    registros += gerar_yoon()

    os.makedirs("anki", exist_ok=True)
    destino = os.path.join("anki", "kana-fase0.tsv")

    with open(destino, "w", encoding="utf-8") as f:
        # Diretivas que o Anki moderno le para configurar a importacao sozinho
        f.write("#separator:tab\n")
        f.write("#html:false\n")
        f.write("#notetype:Basic (and reversed card)\n")
        f.write("#deck:Japones::Fase 0 - Kana\n")
        f.write("#tags column:3\n")
        for kana, leitura, tags in registros:
            f.write(f"{kana}\t{leitura}\t{tags}\n")

    total = len(registros)
    hira = sum(1 for r in registros if "hiragana" in r[2] and "yoon" not in r[2] and "dakuten" not in r[2])
    kata = sum(1 for r in registros if "katakana" in r[2])
    dak = sum(1 for r in registros if "dakuten" in r[2])
    yoon = sum(1 for r in registros if "yoon" in r[2])
    print(f"{destino}: {total} cartoes")
    print(f"  hiragana base : {hira}")
    print(f"  katakana base : {kata}")
    print(f"  dakuten       : {dak}")
    print(f"  yoon          : {yoon}")
    print(f"  (cartoes reversos dobram isso na pratica: {total*2} revisoes por ciclo)")


if __name__ == "__main__":
    main()
