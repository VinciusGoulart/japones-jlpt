"""Aponta o sistema para um diretório descartável ANTES de qualquer import de
`japones` — o config lê as variáveis na importação. Teste nenhum toca o banco
nem o diário de verdade (AGENTS.md, regra 7)."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="japones-teste-")
os.environ["JAPONES_DADOS"] = _TMP
os.environ["JAPONES_DB"] = os.path.join(_TMP, "estudo.db")
os.environ["JAPONES_DIARIO"] = os.path.join(_TMP, "diario.md")
