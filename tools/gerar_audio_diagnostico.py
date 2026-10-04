#!/usr/bin/env python3
"""
Grava em mp3 as falas do 聴解 do diagnostico mensal: um arquivo por questao em
diagnostico/audio/AAAA-MM/<id da questao>.mp3, mais audio/teste.mp3.

POR QUE EXISTE: ate 03/10/2026 a pagina falava com a voz do NAVEGADOR
(speechSynthesis). No Firefox do Linux essa voz e o espeak-ng, que nao
pronuncia japones de forma inteligivel — ele testou antes do Diagnostico #1 e
"nao da para entender direito". Voz do navegador e variavel fora do nosso
controle; audio gravado toca igual no Firefox, no Chrome e no celular.

VOZES: Nanami (mulher e narradora) e Keita (homem), neurais, pelo edge-tts
(servico de leitura em voz alta do Edge; precisa de rede). O texto das falas
sai desta maquina para la — sao so as frases da prova.

TEXTO FALADO: o campo "t" (com kanji) sem os espacos, porque a voz neural acerta
a entonacao a partir da escrita normal. O campo "tts" (kana) continua valendo
so para a voz do navegador. Se um kanji tiver leitura ambigua (明日, 一日, 方),
ponha na fala um "audio_txt" com SO aquela palavra em kana.

EU NAO OUCO O RESULTADO: o script confere que cada fala gerou som e a duracao
final, nao a pronuncia. A pagina tem um botao "Testar o som" para ele conferir
sem gastar as repeticoes da prova.

Dependencia, fora do repo e fora do Python do sistema:
  python3 -m pip install --target ~/.local/share/japones/pylibs edge-tts

A pagina so usa a gravacao se a prova declarar o campo "audio" (o script
imprime a linha). Sem ele, cai na voz do navegador e avisa na tela.

Uso:  python3 tools/gerar_audio_diagnostico.py AAAA-MM
Depois: gravar o JSON no banco da pagina e publicar os mp3 como arquivos dela.
Os mp3 ficam fora do git (sao regeneraveis).
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile

PYLIBS = os.path.expanduser("~/.local/share/japones/pylibs")
PROVAS = "diagnostico/provas"
SAIDA = "diagnostico/audio"

VOZES = {
    "F": {"voice": "ja-JP-NanamiNeural", "pitch": "+0Hz"},
    "M": {"voice": "ja-JP-KeitaNeural", "pitch": "+0Hz"},
    # A narradora divide a voz com a mulher do dialogo: tom mais grave para
    # nao parecer que a pergunta e a primeira fala sao da mesma pessoa.
    "N": {"voice": "ja-JP-NanamiNeural", "pitch": "-18Hz"},
}
RITMO = "-15%"  # o N5 real e falado devagar; a voz neural, no padrao, e ritmo de noticiario
NOME_VOZES = "Nanami + Keita (gravado)"

# Pausas em segundos. As falas sao aparadas antes, entao o silencio e so este.
P_BORDA = 0.35
P_TURNO = 0.45
P_PERGUNTA = 1.1

TESTE = [
    ("N", "音のテストです。"),
    ("F", "こんにちは。聞こえますか。"),
    ("M", "はい、よく聞こえます。"),
]


def texto_falado(fala):
    return (fala.get("audio_txt") or fala["t"]).replace(" ", "").replace("　", "")


def roteiro(q):
    """[(quem, texto) | pausa] — pergunta, dialogo, pergunta de novo, como no JLPT."""
    falas = []
    for i, f in enumerate(q["falas"]):
        if i:
            falas.append(P_TURNO)
        falas.append((f["v"], texto_falado(f)))
    if not q.get("pergunta"):
        return falas
    p = ("N", (q.get("pergunta_audio") or q["pergunta"]).replace(" ", "").replace("　", ""))
    return [p, P_PERGUNTA] + falas + [P_PERGUNTA, p]


def rodar(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ffmpeg falhou: " + " ".join(cmd) + "\n" + r.stderr[-800:])
    return r.stdout


def duracao(caminho):
    out = rodar(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", caminho])
    return float(out.strip())


async def sintetizar(edge_tts, quem, texto, destino):
    v = VOZES[quem]
    await edge_tts.Communicate(texto, v["voice"], rate=RITMO, pitch=v["pitch"]).save(destino)


def montar(edge_tts, itens, destino, tmp):
    """Sintetiza cada fala, apara o silencio das pontas e costura com as pausas."""
    partes = []
    for n, item in enumerate([P_BORDA] + itens + [P_BORDA]):
        wav = os.path.join(tmp, f"p{n}.wav")
        if isinstance(item, float):
            rodar(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", str(item),
                   "-i", "anullsrc=r=24000:cl=mono", wav])
        else:
            quem, texto = item
            bruto = os.path.join(tmp, f"p{n}.mp3")
            asyncio.run(sintetizar(edge_tts, quem, texto, bruto))
            if not os.path.exists(bruto) or os.path.getsize(bruto) < 2000:
                sys.exit(f"A voz nao devolveu som para: {texto}")
            apara = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04,"
                     "areverse,"
                     "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,"
                     "areverse")
            rodar(["ffmpeg", "-y", "-v", "error", "-i", bruto, "-af", apara,
                   "-ar", "24000", "-ac", "1", wav])
            if duracao(wav) < 0.25:
                sys.exit(f"Fala curta demais depois de aparar ({duracao(wav):.2f}s): {texto}")
        partes.append(wav)
    lista = os.path.join(tmp, "lista.txt")
    with open(lista, "w") as f:
        f.writelines(f"file '{p}'\n" for p in partes)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    rodar(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lista,
           "-c:a", "libmp3lame", "-b:a", "64k", "-ar", "24000", "-ac", "1", destino])
    for p in partes:
        os.remove(p)
    return duracao(destino)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    prova_id = sys.argv[1]
    caminho = os.path.join(PROVAS, prova_id + ".json")
    if not os.path.exists(caminho):
        sys.exit(f"Nao achei {caminho}. Rode a partir da raiz do repositorio.")

    sys.path.insert(0, PYLIBS)
    try:
        import edge_tts
    except ImportError:
        sys.exit("Falta o edge-tts. Instale com:\n"
                 f"  python3 -m pip install --target {PYLIBS} edge-tts")

    with open(caminho, encoding="utf-8") as f:
        prova = json.load(f)
    chokai = [s for s in prova["secoes"] if s["id"] == "chokai"]
    if not chokai:
        sys.exit("A prova nao tem secao de 聴解.")

    publicar = {}
    with tempfile.TemporaryDirectory() as tmp:
        rel = "audio/teste.mp3"
        seg = montar(edge_tts, [x for i, t in enumerate(TESTE) for x in ([P_TURNO] if i else []) + [t]],
                     os.path.join("diagnostico", rel), tmp)
        publicar[rel] = os.path.join("diagnostico", rel)
        print(f"  {rel:<28} {seg:5.1f}s  (teste de som)")

        for q in chokai[0]["questoes"]:
            rel = f"audio/{prova_id}/{q['id']}.mp3"
            seg = montar(edge_tts, roteiro(q), os.path.join("diagnostico", rel), tmp)
            publicar[rel] = os.path.join("diagnostico", rel)
            print(f"  {rel:<28} {seg:5.1f}s  {len(q['falas'])} fala(s)"
                  + ("" if q.get("pergunta") else ", sem pergunta"))

    campo = {"voz": NOME_VOZES, "base": f"audio/{prova_id}/", "teste": "audio/teste.mp3"}
    if prova.get("audio") == campo:
        print(f"\n{caminho} ja declara o audio.")
    else:
        print(f"\nFalta declarar o audio em {caminho} (no nivel de \"id\"):")
        print('  "audio": ' + json.dumps(campo, ensure_ascii=False) + ",")
    print("Depois: gravar o JSON em provas/" + prova_id + " no banco da pagina e publicar estes arquivos:")
    print(json.dumps(publicar, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
