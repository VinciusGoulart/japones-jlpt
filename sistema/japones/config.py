"""Caminhos e constantes do sistema.

Tudo que é pessoal (banco, backups) mora FORA do repositório, que é público.
Os caminhos podem ser trocados por variável de ambiente — é assim que os testes
rodam contra um banco descartável sem tocar no de verdade.
"""
import os
from datetime import date
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]
TOOLS = RAIZ_REPO / "tools"
DIARIO = Path(os.environ.get("JAPONES_DIARIO", RAIZ_REPO / "progresso" / "diario.md"))
ESTADO = RAIZ_REPO / "progresso" / "estado.json"
CURRICULO = RAIZ_REPO / "plano" / "curriculo.md"

DADOS = Path(os.environ.get("JAPONES_DADOS", Path.home() / ".local" / "share" / "japones"))
BANCO = Path(os.environ.get("JAPONES_DB", DADOS / "estudo.db"))
BACKUP = DADOS / "backup-progresso"

# O dia de estudo vira às 04:00, o mesmo relógio do Anki (regra unificada em 13/09).
ROLLOVER_H = 4
INICIO_PLANO = date(2026, 8, 3)
