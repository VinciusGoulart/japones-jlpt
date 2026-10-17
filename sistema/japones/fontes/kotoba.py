#!/usr/bin/env python3
"""
Lê o Kotoba — o dicionário JP⇄PT-BR offline dele (app Flutter, código em
~/Documentos/facul/dictionary) — e devolve palavras, kanji, o histórico de
buscas e as listas em dicionários Python.

Existe por dois motivos. (1) O Kotoba é onde ele procura palavra no dia a dia,
então o histórico é o retrato mais honesto do que ele encontrou fora da mesa:
o que leu, o que não entendeu, o que procurou duas vezes. (2) O banco do
dicionário dá leitura, glosa PT, nível JLPT e acento tonal com a MESMA fonte
que ele vê na tela — o tutor confere em vez de lembrar (regra 1 do CLAUDE.md:
nunca inventar japonês).

FONTES (contrato em dictionary/docs/DESIGN.md §5; as consultas abaixo são
cópias das consultas nomeadas de §5.5, com o nome no comentário):
  - dicionário: <pasta>/db/kotoba-s3-*.db — esquema 3, o app NUNCA escreve
    nele; aberto com mode=ro&immutable=1.
  - usuário:    <pasta>/user.db — WAL, o app pode estar aberto gravando; lido
    de uma CÓPIA em tmp, como o tools/anki_status.py faz com a coleção do Anki.
  <pasta> = ~/.local/share/app.kotoba.dicionario (ou $JAPONES_KOTOBA).

SÓ LÊ. Nunca escreve em nenhum dos dois bancos, nunca migra, nunca cria
arquivo ao lado deles. O user.db é dele: favoritos e histórico que um bug meu
apagasse não voltam.

Uso:  python3 sistema/japones/fontes/kotoba.py buscar 持つ [limite] [--sentidos]
      python3 sistema/japones/fontes/kotoba.py buscar comprar
      python3 sistema/japones/fontes/kotoba.py kanji 食
      python3 sistema/japones/fontes/kotoba.py historico [n]
      python3 sistema/japones/fontes/kotoba.py listas
      (de dentro de sistema/: python3 -m japones.fontes.kotoba buscar 持つ)

Só biblioteca padrão: roda com o python3 do sistema, sem venv.
"""
from __future__ import annotations

import functools
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

__all__ = [
    "KotobaIndisponivel",
    "caminho_dicionario",
    "caminho_user_db",
    "buscar",
    "kanji",
    "historico",
    "listas",
]

PASTA_PADRAO = Path.home() / ".local" / "share" / "app.kotoba.dicionario"

# Esquemas que este módulo sabe ler. O 2 trouxe kanji_mnemonic (lida em kanji());
# o 3 só mexeu em frases de exemplo, que não são lidas aqui.
ESQUEMA_MINIMO = 2
ESQUEMA_CONHECIDO = 3

# gloss.src (DESIGN §5.1.6): 0 JMdict original (só EN) · 1 LLM · 2 MT · 3 humano ·
# 4 reuso de tradução LLM · 5 MT rejeitada (texto = cópia do EN) · 9 placeholder.
# O app põe o selo "tradução automática" em 2, 4, 5 e 9 (§7.9) — o reuso LLM fora
# de contexto conta como automático "por honestidade" (decisão C31). Aqui é igual.
SRC_AUTOMATICA = frozenset((2, 4, 9))
SRC_REJEITADA = 5  # o app não mostra o PT dessa glosa; aqui ela também sai

# Tentativas de copiar o user.db sem o app escrever no meio da cópia.
_TENTATIVAS_COPIA = 5


class KotobaIndisponivel(Exception):
    """O Kotoba não está instalado neste PC, ou o banco não abriu.

    Quem chama trata como fonte fora do ar (DESIGN do sistema §6: nenhuma
    fonte externa derruba uma ferramenta).
    """


# ------------------------------------------------------------------ caminhos


def _pasta() -> Path:
    return Path(os.environ.get("JAPONES_KOTOBA") or PASTA_PADRAO).expanduser()


_NOME_DB = re.compile(r"kotoba-s(\d+)-([0-9.]+)-")


def caminho_dicionario() -> Path:
    """O banco do dicionário instalado mais novo.

    Nome instalado: kotoba-s{esquema}-{versão dos dados}-{sha12}.db (§5.1.1).
    Preferência: esquema que este módulo conhece > esquema maior > versão dos
    dados maior > mtime mais recente.
    """
    pasta = _pasta() / "db"
    candidatos = [p for p in pasta.glob("kotoba-s*.db") if p.is_file()]
    if not candidatos:
        raise KotobaIndisponivel(
            f"dicionário do Kotoba não encontrado em {pasta} "
            "(o app instala o banco na 1ª vez que abre neste PC)"
        )

    def chave(p: Path):
        m = _NOME_DB.match(p.name)
        esquema, versao = (int(m.group(1)), m.group(2)) if m else (0, "")
        return (esquema <= ESQUEMA_CONHECIDO, esquema, versao, p.stat().st_mtime)

    return max(candidatos, key=chave)


def caminho_user_db() -> Path:
    """O banco do usuário (histórico, listas, notas)."""
    p = _pasta() / "user.db"
    if not p.is_file():
        raise KotobaIndisponivel(f"user.db do Kotoba não encontrado em {p}")
    return p


# ------------------------------------------------------------------ conexões


@functools.lru_cache(maxsize=2)
def _abrir_dicionario(caminho: str) -> sqlite3.Connection:
    # immutable=1: o SQLite não procura -wal/-journal nem trava o arquivo — e não
    # cria nada ao lado dele. O app abre assim também (§5.1.1). as_uri() escapa
    # espaço, '#', '?' e '%' no caminho, que quebrariam o URI montado na mão.
    uri = Path(caminho).resolve().as_uri() + "?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = 1")
    con.execute("PRAGMA cache_size = -16000")
    esquema = con.execute("PRAGMA user_version").fetchone()[0]
    if esquema < ESQUEMA_MINIMO:
        con.close()
        raise KotobaIndisponivel(
            f"dicionário com esquema {esquema}; este leitor precisa do {ESQUEMA_MINIMO} ou mais"
        )
    return con


def _dicionario() -> sqlite3.Connection:
    """Conexão (reaproveitada entre chamadas) com o banco do dicionário."""
    caminho = caminho_dicionario()
    try:
        return _abrir_dicionario(str(caminho))
    except sqlite3.Error as e:
        raise KotobaIndisponivel(f"não consegui abrir {caminho.name}: {e}") from e


def _assinatura(p: Path):
    try:
        st = p.stat()
    except FileNotFoundError:
        return None
    return (st.st_mtime_ns, st.st_size)


def _copiar_user_db(original: Path, pasta: Path) -> tuple[Path, bool]:
    """Copia user.db (+ -wal) para `pasta`. Devolve (cópia, estável): estável =
    o app não gravou durante a cópia (mtime e tamanho iguais antes e depois).

    Com o app ABERTO, as gravações recentes vivem no -wal: copiar só o arquivo
    principal devolveria um retrato velho (foi o que escondeu 371 notas no
    anki_status em 30/08). O -shm NÃO vem, de propósito: é só um índice do -wal,
    o SQLite o reconstrói a partir do -wal ao abrir a cópia, e um -shm copiado
    num instante diferente do -wal é o único jeito de ler páginas trocadas.
    """
    wal = original.with_name(original.name + "-wal")
    antes = (_assinatura(original), _assinatura(wal))
    copia = pasta / "user.db"
    shutil.copyfile(original, copia)
    if antes[1] is not None:
        try:
            shutil.copyfile(wal, pasta / "user.db-wal")
        except FileNotFoundError:  # o app fechou e o checkpoint apagou o -wal
            return copia, False
    depois = (_assinatura(original), _assinatura(wal))
    return copia, antes == depois


def _ler_user_db(ler):
    """Roda `ler(con)` sobre uma cópia do user.db e apaga a cópia.

    Se o app gravar no meio da cópia, tenta de novo. Na ÚLTIMA tentativa aceita
    uma cópia instável só se o PRAGMA quick_check passar — cópia rasgada nunca é
    lida. Medido em 17/10/2026 com um escritor em WAL e checkpoints forçados no
    meio: 1.000 gravações/s → 0 falhas em 1.680 leituras, todas vendo as linhas
    que ainda estavam no -wal; 20/s → 0 em 8.998. Só com o escritor em laço
    apertado (~90 mil/s, o banco inchando para 28 MB) as 5 tentativas se esgotam
    e sai KotobaIndisponivel. O app grava uma linha de histórico por Enter.
    """
    original = caminho_user_db()
    erro = "o app gravou durante todas as tentativas de cópia"
    for tentativa in range(_TENTATIVAS_COPIA):
        ultima = tentativa == _TENTATIVAS_COPIA - 1
        pasta = Path(tempfile.mkdtemp(prefix="kotoba-user-"))
        try:
            copia, estavel = _copiar_user_db(original, pasta)
            if estavel or ultima:
                # A cópia abre em leitura e escrita para o SQLite poder reaplicar o
                # -wal nela (e criar o -shm) — tudo dentro da pasta temporária.
                con = sqlite3.connect(copia)
                try:
                    con.row_factory = sqlite3.Row
                    con.execute("PRAGMA query_only = 1")
                    if not estavel:
                        resultado = con.execute("PRAGMA quick_check").fetchone()[0]
                        if resultado != "ok":
                            raise sqlite3.DatabaseError(f"quick_check: {resultado}")
                    return ler(con)
                finally:
                    con.close()
        except (sqlite3.DatabaseError, OSError) as e:
            erro = f"{type(e).__name__}: {e}"
        finally:
            shutil.rmtree(pasta, ignore_errors=True)
        if not ultima:
            time.sleep(0.02 * (tentativa + 1))
    raise KotobaIndisponivel(f"não consegui ler uma cópia consistente do user.db ({erro})")


# ------------------------------------------------------------------ normalização (§5.4)
# Porte das funções de dictionary/tools/dict_builder/kotoba_build/jnorm.py, que é a
# referência Python do contrato. Mudou lá? Muda aqui.

_LINHAS_VOGAL = (
    ("あかさたなはまやらわがざだばぱぁゃゎゕ", "あ"),
    ("いきしちにひみりぎじぢびぴぃゐ", "い"),
    ("うくすつぬふむゆるぐずづぶぷぅゅゔ", "う"),
    ("えけせてねへめれげぜでべぺぇゑゖ", "え"),
    ("おこそとのほもよろをごぞどぼぽぉょ", "お"),
)
_VOGAL_DE = {ch: vogal for linha, vogal in _LINHAS_VOGAL for ch in linha}
_KATA_PARA_HIRA = {cp: cp - 0x60 for cp in range(0x30A1, 0x30F7)}
_KATA_PARA_HIRA[ord("ヽ")] = ord("ゝ")
_KATA_PARA_HIRA[ord("ヾ")] = ord("ゞ")
_TOKEN = re.compile(r"[^\W_]+")  # sequência máxima de letras/números (≈ unicode61)
_ENCLITICOS = frozenset(("se", "me", "te", "nos", "vos", "lo", "la", "los", "las", "lhe", "lhes"))


def norm_ja(s: str) -> str:
    """Chave japonesa (§5.4.1): NFKC, minúsculas, 〜→~, katakana→hiragana, ー→vogal.

    >>> norm_ja("ｺｰﾋｰ"), norm_ja("ヴァイオリン")
    ('こおひい', 'ゔぁいおりん')
    """
    s = unicodedata.normalize("NFKC", s).lower().replace("〜", "~")
    s = s.translate(_KATA_PARA_HIRA)
    if "ー" not in s:
        return s
    out: list[str] = []
    for ch in s:
        if ch == "ー" and out and out[-1] in _VOGAL_DE:
            out.append(_VOGAL_DE[out[-1]])
        else:
            out.append(ch)
    return "".join(out)


def fold(s: str) -> str:
    """Minúsculas + NFKD sem as marcas combinantes (§5.4.3): 'Coração' → 'coracao'."""
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def query_tokens(q: str) -> list[str]:
    """Tokens de uma consulta latina, como o tokenizer do FTS os vê (§5.4.3)."""
    return _TOKEN.findall(fold(q))


def ntok_of(s: str, lang: str) -> int:
    """Nº de tokens; em PT sem contar enclíticos com hífen ('sentar-se' → 1)."""
    dobrado = fold(s)
    n = 0
    for m in _TOKEN.finditer(dobrado):
        ini = m.start()
        if lang == "pt" and m.group() in _ENCLITICOS and ini > 0 and dobrado[ini - 1] == "-":
            continue
        n += 1
    return n


def fts_phrase(tokens: list[str]) -> str:
    """Frase FTS5 '"a b"' (aspas internas dobradas). Nunca repassa operador digitado."""
    return '"' + " ".join(t.replace('"', '""') for t in tokens) + '"'


# Variantes de singular/masculino do último token PT (§6.4.1, §15.5) — porte de
# packages/kotoba_core/lib/src/query/pt_variants.dart.
PENALIDADE_SINGULAR = 30
PENALIDADE_LEXICALIZADO = 1000
PENALIDADE_MASCULINO = 2000
_SEM_SINGULAR = frozenset(
    "mais jamais demais deus cais lapis onibus virus tenis pires simples ferias atlas oculos caos "
    "eles elas voces todos todas ambos ambas outros outras alguns algumas muitos muitas poucos "
    "poucas varios varias quantos quantas".split()
)
_LEXICALIZADOS = frozenset("melhoras humanidades avos observacoes memorias valores legendas".split())
_PLURAIS_FIXOS = {"reis": "rei", "leis": "lei", "bois": "boi", "pais": "pai", "herois": "heroi", "maes": "mae"}
_REGRAS_PLURAL = (  # (terminação, singulares em ordem de preferência, nº mínimo de letras)
    ("oes", ("ao",), 0), ("aes", ("ao",), 0), ("aos", ("ao",), 0),
    ("ais", ("al", "ai"), 0), ("eis", ("el", "il", "ei"), 0), ("ois", ("ol", "oi"), 0),
    ("uis", ("ul",), 0), ("is", ("i", "il"), 5), ("ns", ("m", "n"), 0),
    ("res", ("r", "re"), 0), ("zes", ("z", "ze"), 0), ("ses", ("s", "se"), 0),
    ("s", ("",), 0),
)


def _singulares(w: str) -> list[str]:
    if w in _SEM_SINGULAR:
        return []
    if w in _PLURAIS_FIXOS:
        return [_PLURAIS_FIXOS[w]]
    for sufixo, trocas, minimo in _REGRAS_PLURAL:
        if len(w) >= minimo and w.endswith(sufixo):
            raiz = w[: len(w) - len(sufixo)]
            return [raiz + t for t in trocas]
    return []


def variantes_pt(tokens: list[str]) -> list[tuple[list[str], int]]:
    """[(tokens, penalidade)]: original (0), singulares (30; 1000 se lexicalizado), masculino (2000).

    >>> [" ".join(t) for t, _ in variantes_pt(["casas"])]
    ['casas', 'casa', 'caso']
    """
    if not tokens:
        return []
    saida = [(list(tokens), 0)]
    ultimo = tokens[-1]
    if len(ultimo) < 4:
        return saida
    sing = _singulares(ultimo)
    pen = PENALIDADE_LEXICALIZADO if ultimo in _LEXICALIZADOS else PENALIDADE_SINGULAR
    vistos = {ultimo}
    for s in sing:
        if s not in vistos:
            vistos.add(s)
            saida.append((tokens[:-1] + [s], pen))
    base = sing[0] if sing else ultimo
    if base.endswith("a"):
        masc = base[:-1] + "o"
        if masc not in vistos:
            saida.append((tokens[:-1] + [masc], PENALIDADE_MASCULINO))
    return saida


def _e_japones(ch: str) -> bool:
    """Kana ou kanji (como Kana.containsJapanese); ・ ゛ ゜ ゠ sozinhos não contam."""
    cp = ord(ch)
    if 0x3099 <= cp <= 0x309C or cp in (0x30A0, 0x30FB):
        return False
    return (
        0x3041 <= cp <= 0x30FF          # hiragana e katakana (inclui ー)
        or 0xFF66 <= cp <= 0xFF9D       # katakana de meia largura
        or 0x3400 <= cp <= 0x4DBF       # CJK extensão A
        or 0x4E00 <= cp <= 0x9FFF       # CJK unificado
        or 0xF900 <= cp <= 0xFAFF       # CJK de compatibilidade
        or 0x20000 <= cp <= 0x3134F     # CJK extensões B–G
        or cp in (0x3005, 0x3006, 0x3007)  # 々 〆 〇
    )


def _e_kana(ch: str) -> bool:
    return "ぁ" <= ch <= "ヿ" or "ｦ" <= ch <= "ﾝ"


_FICAM_NAS_PONTAS = frozenset("〜～~ー")


def _limpar_pontas_ja(s: str) -> str:
    """Tira pontuação, símbolos e espaços das pontas ('「猫」' → '猫', '食べた。' → '食べた').

    Como o app com allowWildcards = false (§6.4): * e ? também saem das pontas.
    """
    def sai(ch: str) -> bool:
        return ch not in _FICAM_NAS_PONTAS and (ch.isspace() or unicodedata.category(ch)[0] in "PSZ")

    i, j = 0, len(s)
    while i < j and sai(s[i]):
        i += 1
    while j > i and sai(s[j - 1]):
        j -= 1
    return s[i:j]


# ------------------------------------------------------------------ SQL do dicionário (§5.5)

# SQL_JA_EXACT — só o ramo exato (tiers 0 texto idêntico · 1 chave normalizada).
SQL_JA_EXACT = """
SELECT id >> 7 AS eid, MIN(CASE WHEN text = :raw THEN 0 ELSE 1 END) AS tier,
       MAX(rk) >> 7 AS score, MAX(rk) & 127 AS fpri, MIN(length(coalesce(norm, text))) AS len
FROM form WHERE coalesce(norm, text) = :q
GROUP BY eid
ORDER BY tier, MAX(rk) DESC, len, eid
LIMIT :limit"""


def _sql_ja_prefixo(curta: bool) -> str:
    """SQL_JA_EXACT_PREFIX (curta=False) e SQL_JA_EXACT_PREFIX_SHORT (chave de 1–2
    code points: o ramo de prefixo só vê formas com score ≥ 60, pelo índice parcial
    form_key_hi; o literal 7680 = 60 << 7)."""
    filtro = " AND rk >= 7680" if curta else ""
    return f"""
WITH m(fid, rk, len, tier) AS (
  SELECT id, rk, length(coalesce(norm, text)), CASE WHEN text = :raw THEN 0 ELSE 1 END
  FROM form WHERE coalesce(norm, text) = :q
  UNION ALL
  SELECT id, rk, length(coalesce(norm, text)), 3
  FROM form WHERE coalesce(norm, text) > :q AND coalesce(norm, text) < :q_hi{filtro}
)
SELECT fid >> 7 AS eid, MIN(tier) AS tier, MAX(rk) >> 7 AS score, MAX(rk) & 127 AS fpri, MIN(len) AS len
FROM m
GROUP BY eid
ORDER BY tier, MAX(rk) DESC, len, eid
LIMIT :limit"""


SQL_JA_EXACT_PREFIX = _sql_ja_prefixo(curta=False)
SQL_JA_EXACT_PREFIX_SHORT = _sql_ja_prefixo(curta=True)


def _sql_glosas(fts: str, com_prefixo: bool) -> str:
    """SQL_GLOSS_PT / _PT_NOPREFIX / _EN / _EN_NOPREFIX (o app as escreve por extenso;
    o texto gerado aqui é o mesmo). Tiers: 0 exata · 1 começa com · 2 palavra(s)
    inteira(s) · 3 prefixo de palavra. `rank` menor = melhor; `sense`/`gloss` = sentido
    (base 0) e posição da glosa de menor rank da entrada (§15.4)."""
    ramo_prefixo = f"""
  UNION ALL
  SELECT rid, 3 FROM (SELECT rowid AS rid FROM {fts} WHERE {fts} MATCH :q_prefix
                      ORDER BY rowid LIMIT :k)""" if com_prefixo else ""
    return f"""
WITH hits(rid, tier) AS (
  SELECT rid, 0 FROM (SELECT rowid AS rid FROM {fts} WHERE {fts} MATCH :q_start
                      AND (rowid & 15) = :qtok ORDER BY rowid LIMIT :k)
  UNION ALL
  SELECT rid, 1 FROM (SELECT rowid AS rid FROM {fts} WHERE {fts} MATCH :q_start
                      ORDER BY rowid LIMIT :k)
  UNION ALL
  SELECT rid, 2 FROM (SELECT rowid AS rid FROM {fts} WHERE {fts} MATCH :q_phrase
                      ORDER BY rowid LIMIT :k){ramo_prefixo}
),
best(eid, tier, score, code) AS (
  SELECT (rid >> 16) & 0xFFFFFF, MIN(tier), 127 - MIN(rid >> 40),
         MIN((tier * 1000 + 20 * MIN((rid >> 9) & 31, 5) + 3 * MIN((rid >> 4) & 31, 5) - (127 - (rid >> 40))) * 1024
             + ((rid >> 4) & 1023))
  FROM hits
  GROUP BY 1
)
SELECT eid, tier, score, code >> 10 AS rank, (code >> 5) & 31 AS sense, code & 31 AS gloss
FROM best
ORDER BY rank, eid
LIMIT :limit"""


SQL_GLOSS_PT = _sql_glosas("gloss_pt_fts", com_prefixo=True)
SQL_GLOSS_PT_NOPREFIX = _sql_glosas("gloss_pt_fts", com_prefixo=False)
SQL_GLOSS_EN = _sql_glosas("gloss_en_fts", com_prefixo=True)
SQL_GLOSS_EN_NOPREFIX = _sql_glosas("gloss_en_fts", com_prefixo=False)

# SQL_VERB_PT — o verbo PT da entrada ("estudar" → 勉強); rank já inclui o +5.
SQL_VERB_PT = """
WITH hits(rid, tier) AS (
  SELECT rid, 0 FROM (SELECT rowid AS rid FROM verb_pt_fts WHERE verb_pt_fts MATCH :q_start
                      AND (rowid & 15) = :qtok ORDER BY rowid LIMIT :k)
  UNION ALL
  SELECT rid, 1 FROM (SELECT rowid AS rid FROM verb_pt_fts WHERE verb_pt_fts MATCH :q_start
                      ORDER BY rowid LIMIT :k)
  UNION ALL
  SELECT rid, 2 FROM (SELECT rowid AS rid FROM verb_pt_fts WHERE verb_pt_fts MATCH :q_phrase
                      ORDER BY rowid LIMIT :k)
)
SELECT (rid >> 4) & 0xFFFFFF AS eid,
       MIN(tier) AS tier,
       127 - MIN(rid >> 28) AS score,
       MIN(tier * 1000 + 5 - (127 - (rid >> 28))) AS rank
FROM hits
GROUP BY eid
ORDER BY rank, eid
LIMIT :limit"""

# Q7 — entrada completa (cada uma é range scan no rowid).
SQL_ENTRY = "SELECT id, score, jlpt, flags, infl, disp_k, disp_r FROM entry WHERE id = :eid"
SQL_FORMS = """
SELECT (id >> 6) & 1 AS kind, id & 63 AS ord, text, rk & 127 AS fpri, inf, restr, pitch
FROM form WHERE id BETWEEN :eid << 7 AND (:eid << 7) | 127 ORDER BY id"""
SQL_SENSES = """
SELECT id & 31 AS ord, pos, misc, field, dial, stagk, stagr, extra
FROM sense WHERE id BETWEEN :eid << 5 AND (:eid << 5) | 31 ORDER BY id"""
SQL_GLOSSES = """
SELECT (id >> 10) & 3 AS lang, (id >> 5) & 31 AS sense, id & 31 AS ord, src, type, text
FROM gloss WHERE id BETWEEN :eid << 12 AND (:eid << 12) | 4095 ORDER BY id"""

# Q9 / Q11 — kanji.
SQL_KANJI = """
SELECT cp, strokes, grade, freq, jlpt_old, jlpt, radical, rad_var, onyomi, kunyomi, nanori,
       mean_en, mean_pt, mean_pt_src, variants
FROM kanji WHERE cp = :cp"""
SQL_KANJI_COMPONENTS = """
SELECT c.id, c.radk_char, c.glyph, c.glyph_alt, c.strokes, c.radical, c.variant, c.label_pt
FROM kanji_component kc JOIN component c ON c.id = kc.comp
WHERE kc.cp = :cp ORDER BY c.strokes, c.id"""
SQL_RADICAL = """
SELECT r.num, r.glyph, r.name_ja, r.name_romaji, r.mean_pt, r.mean_en, r.strokes,
       v.id AS var_id, v.glyph AS var_glyph, v.position, v.position_sub, v.name_ja AS var_name_ja,
       v.name_romaji AS var_name_romaji, v.mean_pt AS var_mean_pt
FROM radical r LEFT JOIN radical_variant v ON v.id = :var AND v.radical = r.num
WHERE r.num = :num"""
SQL_KANJI_MNEMONIC = "SELECT meaning, reading_kana, reading_text FROM kanji_mnemonic WHERE cp = :cp"


# ------------------------------------------------------------------ busca


def buscar(termo: str, limite: int = 5, *, detalhado: bool = False) -> list[dict]:
    """Procura `termo` no dicionário, com a ordem do próprio app.

    Japonês (kanji ou kana, qualquer largura/katakana): casamento EXATO com
    grafias ou leituras pela chave de §5.4.1 (SQL_JA_EXACT); só se não houver
    nenhum, cai para o prefixo (SQL_JA_EXACT_PREFIX[_SHORT]), marcado em
    "casamento". Ordem: tier, score, prioridade da forma, comprimento.

    Latim: glosas em português pelo FTS do app (SQL_GLOSS_PT + SQL_VERB_PT, com
    as variantes de plural/masculino de §6.4.1, mescladas por rank+penalidade);
    se o português não encher `limite`, as glosas em inglês (SQL_GLOSS_EN)
    completam a lista, sem repetir entrada — a seção Inglês do app, depois da
    Português.

    SIMPLIFICADO em relação ao app (§7.5.1):
      - sem deflexão: 食べた / 買いました não chegam a 食べる / 買う (o
        Deinflector e as regras moram no kotoba_core, em Dart);
      - sem romaji: 'kau' é tratado como português, não como かう;
      - sem curingas (* e ? são literais e saem das pontas), sem substring
        (seção "Contém…"), sem "leitura pelo início" e sem seção Kanji;
      - o prefixo japonês só entra quando o exato não acha nada (no app ele
        completa a lista logo depois dos exatos).

    Cada item: ent_seq, palavra (o título que o app mostra: a grafia kanji de
    exibição, ou a leitura se a palavra só tem kana ou costuma ser escrita em kana
    — 珈琲 → コーヒー), grafia_kanji (None se não há), leitura, glosas_pt
    (todas, o 1º sentido primeiro, sem as MT
    rejeitadas), glosas_pt_auto (as de glosas_pt que são tradução automática —
    o app põe selo nelas), glosas_en, jlpt (5 = N5 … 1 = N1, None = sem nível),
    comum, classe (tags de classe do 1º sentido: v5t, v1, adj-i…), acento
    ({leitura, quedas, padroes} ou None), url (kotoba://palavra/N), casamento
    (exato · prefixo · pt · pt-verbo · en), sentido_casado (base 0, nas buscas
    PT/EN) e usual_em_kana. Com detalhado=True, também "sentidos" (classe, misc,
    pt, pt_auto, en por sentido) — fica de fora por padrão porque repete todas
    as glosas, e resposta MCP precisa ser enxuta (AGENTS.md, regra 5).
    """
    termo = (termo or "").strip()
    if not termo or limite <= 0:
        return []
    con = _dicionario()
    if any(_e_japones(ch) for ch in termo):
        acertos = _buscar_japones(con, termo, limite)
    else:
        acertos = _buscar_latim(con, termo, limite)
    saida = []
    for eid, casamento, sentido in acertos:
        item = _montar_entrada(con, eid, casamento, sentido)
        if item is not None:
            if not detalhado:
                del item["sentidos"]
            saida.append(item)
    return saida


def _buscar_japones(con, termo: str, limite: int) -> list[tuple]:
    texto = _limpar_pontas_ja(termo)
    if not texto:
        return []
    chave = norm_ja(texto)
    lim = max(limite, 50)
    linhas = con.execute(SQL_JA_EXACT, {"q": chave, "raw": texto, "limit": lim}).fetchall()
    if not linhas and not (len(chave) == 1 and _e_kana(chave)):
        sql = SQL_JA_EXACT_PREFIX_SHORT if len(chave) <= 2 else SQL_JA_EXACT_PREFIX
        params = {"q": chave, "raw": texto, "q_hi": chave + "\U0010FFFF", "limit": lim}
        linhas = con.execute(sql, params).fetchall()
    return [(l["eid"], "exato" if l["tier"] <= 1 else "prefixo", None) for l in linhas[:limite]]


def _params_fts(tokens: list[str], qtok: int, lim: int) -> dict:
    frase = fts_phrase(tokens)
    return {"q_start": "^" + frase, "q_phrase": frase, "q_prefix": frase + "*",
            "qtok": qtok, "k": 300, "limit": lim}


def _curto(tokens: list[str]) -> bool:
    """1 token de ≤ 2 letras: usa a variante _NOPREFIX ("ar"* percorreria meio índice)."""
    return len(tokens) == 1 and len(tokens[0]) <= 2


def _buscar_latim(con, termo: str, limite: int) -> list[tuple]:
    tokens = query_tokens(termo)
    letras = sum(1 for ch in fold(termo) if ch.isascii() and ch.isalpha())
    if not tokens or letras < 2:  # 1 letra não consulta glosas (§7.5.1)
        return []
    lim = max(limite, 50)
    # eid → (rank+penalidade, verbo?, sentido, glosa, tier, casamento): a tupla ordena
    # como o app desempata (§15.4 item 3): menor rank, glosa antes do verbo PT,
    # menor sentido, menor posição.
    melhores: dict[int, list] = {}

    def anotar(eid, tier, rank, casamento, sentido=None, glosa=None):
        novo = [rank, casamento == "pt-verbo", sentido if sentido is not None else 99,
                glosa if glosa is not None else 99, tier, casamento]
        atual = melhores.get(eid)
        if atual is None:
            melhores[eid] = novo
            return
        menor_tier = min(atual[4], tier)
        if novo[:4] < atual[:4]:
            atual[:] = novo
        atual[4] = menor_tier

    # --- português
    qtok = min(ntok_of(termo, "pt"), 15)

    def rodar_variante(toks: list[str], penalidade: int):
        params = _params_fts(toks, qtok, lim)
        sql = SQL_GLOSS_PT_NOPREFIX if _curto(toks) else SQL_GLOSS_PT
        for r in con.execute(sql, params):
            anotar(r["eid"], r["tier"], r["rank"] + penalidade, "pt", r["sense"], r["gloss"])
        for r in con.execute(SQL_VERB_PT, params):
            anotar(r["eid"], r["tier"], r["rank"] + penalidade, "pt-verbo")

    variantes = variantes_pt(tokens)
    for toks, pen in variantes:
        if pen < PENALIDADE_MASCULINO:
            rodar_variante(toks, pen)
    # Masculino (a→o) só com < 5 acertos fortes: a troca gera outras palavras reais
    # (porta→porto, fruta→fruto, pasta→pasto).
    if sum(1 for h in melhores.values() if h[4] <= 1) < 5:
        for toks, pen in variantes:
            if pen >= PENALIDADE_MASCULINO:
                rodar_variante(toks, pen)

    ordem = sorted(melhores.items(), key=lambda kv: (kv[1][0], kv[0]))
    saida = [(eid, h[5], h[2] if h[2] != 99 else None) for eid, h in ordem[:limite]]

    # --- inglês completa a lista quando o português não enche (como a seção Inglês
    # do app: depois de Português e sem repetir entrada). Sem isso, "to eat" parava
    # num acerto PT solto (ＧｏＴｏイート) e nunca chegava a 食べる.
    if len(saida) < limite:
        en = tokens[1:] if len(tokens) >= 2 and tokens[0] == "to" else tokens
        params = _params_fts(en, min(len(en), 15), lim)
        sql = SQL_GLOSS_EN_NOPREFIX if _curto(en) else SQL_GLOSS_EN
        vistos = set(melhores)
        for r in con.execute(sql, params):  # uma linha por entrada, já em ordem de rank
            if r["eid"] not in vistos:
                vistos.add(r["eid"])
                saida.append((r["eid"], "en", r["sense"]))
                if len(saida) >= limite:
                    break
    return saida


# ------------------------------------------------------------------ montagem da entrada

_PEQUENOS = frozenset("ゃゅょぁぃぅぇぉゎャュョァィゥェォヮ")  # não contam como mora


def _acento(kana: str, pitch: str | None) -> dict | None:
    """form.pitch ('2' ou '0,2', fonte em meta.pitch_source) → quedas e padrões.

    Queda = nº da mora depois da qual o tom cai (0 = sem queda). Padrão como o
    PitchAccent do app: 0 heiban · 1 atamadaka · nº de moras odaka · resto nakadaka.
    """
    if not pitch:
        return None
    moras = sum(1 for ch in kana if ch not in _PEQUENOS)
    quedas: list[int] = []
    for parte in pitch.split(","):
        try:
            q = int(parte)
        except ValueError:
            continue
        if 0 <= q <= moras and q not in quedas:
            quedas.append(q)
    if not quedas:
        return None

    def padrao(q: int) -> str:
        if q == 0:
            return "heiban"
        if q == 1:
            return "atamadaka"
        return "odaka" if q == moras else "nakadaka"

    return {"leitura": kana, "quedas": quedas, "padroes": [padrao(q) for q in quedas]}


def _tags(s: str | None) -> list[str]:
    return s.split(" ") if s else []


def _sem_repetir(itens):
    vistos, saida = set(), []
    for x in itens:
        if x not in vistos:
            vistos.add(x)
            saida.append(x)
    return saida


def _montar_entrada(con, eid: int, casamento: str, sentido_casado: int | None) -> dict | None:
    e = con.execute(SQL_ENTRY, {"eid": eid}).fetchone()
    if e is None:
        return None
    formas = con.execute(SQL_FORMS, {"eid": eid}).fetchall()
    kanji_txt = None
    if e["disp_k"] is not None:
        kanji_txt = next((f["text"] for f in formas if f["kind"] == 0 and f["ord"] == e["disp_k"]), None)
    forma_kana = next((f for f in formas if f["kind"] == 1 and f["ord"] == e["disp_r"]), None)
    leitura = forma_kana["text"] if forma_kana else ""

    glosas: dict[int, dict] = {}
    for g in con.execute(SQL_GLOSSES, {"eid": eid}):
        s = glosas.setdefault(g["sense"], {"pt": [], "auto": [], "en": []})
        if g["lang"] == 1:
            if g["src"] == SRC_REJEITADA:
                continue
            s["pt"].append(g["text"])
            if g["src"] in SRC_AUTOMATICA:
                s["auto"].append(g["text"])
        elif g["lang"] == 0:
            s["en"].append(g["text"])

    sentidos = []
    for s in con.execute(SQL_SENSES, {"eid": eid}):
        gl = glosas.get(s["ord"], {"pt": [], "auto": [], "en": []})
        sentidos.append({
            "classe": _tags(s["pos"]),
            "misc": _tags(s["misc"]),
            "pt": _sem_repetir(gl["pt"]),
            "pt_auto": bool(gl["auto"]),
            "en": gl["en"],
        })

    glosas_pt = _sem_repetir(g for o in sorted(glosas) for g in glosas[o]["pt"])
    automaticas = {g for o in glosas for g in glosas[o]["auto"]}
    # Título como o do app: kana quando o 1º sentido é 'uk' (usually kana) — 珈琲 vira
    # コーヒー, 有る vira ある. A grafia kanji continua em "grafia_kanji".
    usual_em_kana = bool(e["flags"] & 32)
    return {
        "ent_seq": eid,
        "palavra": leitura if (usual_em_kana or not kanji_txt) else kanji_txt,
        "grafia_kanji": kanji_txt,
        "leitura": leitura,
        "glosas_pt": glosas_pt,
        "glosas_pt_auto": [g for g in glosas_pt if g in automaticas],
        "glosas_en": _sem_repetir(g for o in sorted(glosas) for g in glosas[o]["en"]),
        "jlpt": e["jlpt"],                       # 5 = N5 … 1 = N1; None = fora das listas
        "comum": bool(e["flags"] & 1),           # news1/ichi1/spec1/spec2/gai1
        "classe": sentidos[0]["classe"] if sentidos else [],
        "acento": _acento(leitura, forma_kana["pitch"]) if forma_kana else None,
        "url": f"kotoba://palavra/{eid}",
        "casamento": casamento,
        "sentido_casado": sentido_casado,
        "usual_em_kana": usual_em_kana,
        "sentidos": sentidos,
    }


# ------------------------------------------------------------------ kanji


def _json_lista(s: str | None) -> list:
    return json.loads(s) if s else []


def kanji(literal: str) -> dict | None:
    """Ficha do kanji (KANJIDIC2 + traduções + frase de memorização do Kotoba).

    on em katakana e kun em hiragana, como no KANJIDIC2: o ponto separa o
    okurigana ('た.べる') e o hífen marca prefixo/sufixo ('-ぐい'). jlpt: 5 = N5 …
    1 = N1 (listas de Waller); None = fora. mnemonico.significado usa a marcação
    do app: *componente* e **palavra-chave**. None se o literal não é um kanji
    do banco (ou tem mais de um caractere).
    """
    literal = (literal or "").strip()
    if len(literal) != 1:
        return None
    con = _dicionario()
    cp = ord(literal)
    k = con.execute(SQL_KANJI, {"cp": cp}).fetchone()
    if k is None:
        return None
    r = con.execute(SQL_RADICAL, {"num": k["radical"], "var": k["rad_var"]}).fetchone()
    radical = None
    if r is not None:
        radical = {
            "numero": r["num"], "glifo": r["glyph"], "nome": r["name_ja"],
            "romaji": r["name_romaji"], "significado_pt": r["mean_pt"],
            "variante": {
                "glifo": r["var_glyph"], "nome": r["var_name_ja"],
                "posicao": r["position"], "significado_pt": r["var_mean_pt"],
            } if r["var_id"] is not None else None,
        }
    m = con.execute(SQL_KANJI_MNEMONIC, {"cp": cp}).fetchone()
    return {
        "kanji": literal,
        "on": _json_lista(k["onyomi"]),
        "kun": _json_lista(k["kunyomi"]),
        "significados_pt": _json_lista(k["mean_pt"]),
        "significados_pt_auto": k["mean_pt_src"] == 2,  # kanji.mean_pt_src 2 = MT
        "significados_en": _json_lista(k["mean_en"]),
        "jlpt": k["jlpt"],
        "tracos": k["strokes"],
        "serie": k["grade"],        # 1–6 escola, 8 jōyō do ginásio, 9/10 jinmeiyō
        "frequencia": k["freq"],    # posição 1…2501 nos jornais; None = fora
        "radical": radical,
        "componentes": [
            {"glifo": c["glyph"], "nome_pt": c["label_pt"]}
            for c in con.execute(SQL_KANJI_COMPONENTS, {"cp": cp})
        ],
        "mnemonico": {
            "significado": m["meaning"],
            "leitura_kana": m["reading_kana"],
            "leitura_frase": m["reading_text"],
        } if m is not None else None,
        "url": f"kotoba://kanji/{literal}",
    }


# ------------------------------------------------------------------ user.db

SQL_HISTORICO = """
SELECT id, kind, query, mode, entry_id, kanji, label, result_cnt, created_at
FROM history
WHERE (:desde IS NULL OR created_at >= :desde) AND (:ate IS NULL OR created_at < :ate)
ORDER BY created_at DESC, id DESC
LIMIT :limite"""

SQL_LISTAS = """
SELECT id, name, is_favorites, sort_mode, position FROM list
ORDER BY is_favorites DESC, position, id"""

SQL_ITENS = """
SELECT li.list_id, li.kind, li.ref, li.headword, li.reading, li.gloss_pt, li.note,
       li.position, li.added_at, n.note AS minha_nota
FROM list_item li LEFT JOIN entry_note n ON n.kind = li.kind AND n.ref = li.ref
ORDER BY li.list_id, li.position, li.added_at"""


def _ms(dt: datetime | None) -> int | None:
    # datetime ingênuo → .timestamp() o lê como hora local (America/Sao_Paulo aqui).
    return None if dt is None else int(dt.timestamp() * 1000)


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).isoformat(timespec="seconds")


def _url(tipo: str, ref) -> str | None:
    if tipo == "entry" and ref is not None:
        return f"kotoba://palavra/{ref}"
    if tipo == "kanji" and ref:
        return f"kotoba://kanji/{ref}"
    if tipo == "query" and ref:
        return "kotoba://busca?q=" + quote(str(ref), safe="")
    return None


def historico(desde: datetime | None = None, ate: datetime | None = None,
              limite: int = 500) -> list[dict]:
    """Histórico do Kotoba, mais recente primeiro.

    Intervalo meio-aberto [desde, ate), em datetimes locais ingênuos — assim um
    dia de estudo é (dia 04:00, dia+1 04:00) sem sobreposição. O app guarda até
    1.000 linhas e, quando a mesma coisa é repetida em seguida, só atualiza a hora
    (USQL_HISTORY_TOUCH): "quando" é a ÚLTIMA vez, não a primeira.

    Cada item: tipo ('query' | 'entry' | 'kanji'), consulta, modo, ent_seq,
    kanji, rotulo ("食べる · comer"), resultados (nº, só em 'query'), quando
    (ISO-8601 local, sem fuso: '2026-10-17T02:48:49'), quando_ms (epoch ms
    exato, para quem precisa deduplicar) e url (kotoba://…).
    """
    params = {"desde": _ms(desde), "ate": _ms(ate), "limite": max(0, int(limite))}
    linhas = _ler_user_db(lambda con: con.execute(SQL_HISTORICO, params).fetchall())
    saida = []
    for h in linhas:
        ref = {"entry": h["entry_id"], "kanji": h["kanji"], "query": h["query"]}.get(h["kind"])
        saida.append({
            "tipo": h["kind"],
            "consulta": h["query"],
            "modo": h["mode"],
            "ent_seq": h["entry_id"],
            "kanji": h["kanji"],
            "rotulo": h["label"],
            "resultados": h["result_cnt"],
            "quando": _iso(h["created_at"]),
            "quando_ms": h["created_at"],
            "url": _url(h["kind"], ref),
        })
    return saida


def listas() -> list[dict]:
    """Listas do usuário (Favoritos primeiro), com os itens na ordem manual.

    palavra/leitura/glosa_pt são as CÓPIAS que o app guardou ao adicionar (§5.6:
    sobrevivem a mudanças do JMdict). nota = a "Minha nota" da palavra ou do
    kanji (entry_note), senão a nota do item na lista.
    """
    def ler(con):
        return con.execute(SQL_LISTAS).fetchall(), con.execute(SQL_ITENS).fetchall()

    lst, itens = _ler_user_db(ler)
    por_lista: dict[int, list] = {}
    for i in itens:
        por_lista.setdefault(i["list_id"], []).append({
            "tipo": i["kind"],
            "ref": i["ref"],
            "palavra": i["headword"],
            "leitura": i["reading"],
            "glosa_pt": i["gloss_pt"],
            "nota": i["minha_nota"] or i["note"],
            "adicionado": _iso(i["added_at"]),
            "url": _url(i["kind"], i["ref"]),
        })
    return [{
        "id": l["id"],
        "nome": l["name"],
        "favoritos": bool(l["is_favorites"]),
        "ordem": l["sort_mode"],  # como o app ordena na tela; aqui vem sempre a manual
        "total": len(por_lista.get(l["id"], [])),
        "itens": por_lista.get(l["id"], []),
    } for l in lst]


# ------------------------------------------------------------------ linha de comando


def _main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "ajuda"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    try:
        if cmd == "buscar" and args:
            limite = 5
            detalhado = "--sentidos" in args
            args = [a for a in args if a != "--sentidos"]
            if len(args) > 1 and args[-1].isdigit():
                limite = int(args.pop())
            t0 = time.perf_counter()
            saida = buscar(" ".join(args), limite, detalhado=detalhado)
            print(f"# buscar: {len(saida)} resultado(s) em {(time.perf_counter() - t0) * 1000:.1f} ms",
                  file=sys.stderr)
        elif cmd == "kanji" and args:
            saida = kanji(args[0])
        elif cmd == "historico":
            saida = historico(limite=int(args[0]) if args else 20)
        elif cmd == "listas":
            saida = listas()
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except KotobaIndisponivel as e:
        print(f"Kotoba indisponível: {e}", file=sys.stderr)
        return 1
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
