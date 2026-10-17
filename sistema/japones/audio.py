"""Áudio dos exercícios `ouvir` (DESIGN §12.3): mp3 com a voz neural do edge-tts.

A voz é a mesma do diagnóstico mensal (tools/gerar_audio_diagnostico.py), que
existe porque a voz do navegador no Firefox do Linux é o espeak-ng e "não dá para
entender direito" (03/10). Aqui o mp3 é gravado no criar_licao, não na hora de
tocar: a lição tem de funcionar se a rede cair depois de criada.

O nome do arquivo é um hash da fala: a mesma frase reaproveita o mp3, e o nome
não entrega o texto (que é a resposta do exercício).

O tutor não ouve o que gera: aqui só se confere que o arquivo tem som.
"""
import asyncio
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from japones import config, rede  # noqa: F401  (rede: DNS só IPv4 para o bing.com)

VOZES = {"F": "ja-JP-NanamiNeural", "M": "ja-JP-KeitaNeural"}
RITMO = "-15%"      # o N5 real é falado devagar; a voz neural, no padrão, é ritmo de noticiário
NOME = re.compile(r"^[0-9a-f]{20}$")


def pasta() -> Path:
    return config.DADOS / "audio"


def nome(fala: str, voz: str = "F") -> str:
    return hashlib.sha256(f"{voz}|{RITMO}|{fala}".encode()).hexdigest()[:20]


def caminho(n: str) -> Path | None:
    """O mp3 de um nome, ou None se o nome não for um dos nossos (a rota da API recebe texto de fora)."""
    return pasta() / f"{n}.mp3" if NOME.match(n) else None


def garantir(fala: str, voz: str = "F") -> str:
    """Grava o mp3 se ainda não existir e devolve o nome. Levanta RuntimeError sem rede."""
    fala = re.sub(r"[ 　]", "", fala)      # a voz neural entoa melhor a escrita normal, sem os espaços didáticos
    n = nome(fala, voz)
    destino = pasta() / f"{n}.mp3"
    if destino.exists() and destino.stat().st_size > 0:
        return n
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp")
    try:
        _sintetizar(fala, VOZES[voz], tmp)
        if not tmp.exists() or tmp.stat().st_size == 0:
            raise RuntimeError("o edge-tts não devolveu som")
        tmp.replace(destino)
    finally:
        tmp.unlink(missing_ok=True)
    return n


def _sintetizar(texto: str, voz: str, destino: Path) -> None:
    import edge_tts

    async def gravar():
        await edge_tts.Communicate(texto, voz, rate=RITMO).save(str(destino))

    # Numa thread própria: o servidor MCP e a API podem estar dentro de um event loop,
    # e asyncio.run() não roda dentro de outro.
    with ThreadPoolExecutor(1) as ex:
        ex.submit(asyncio.run, gravar()).result(timeout=60)
