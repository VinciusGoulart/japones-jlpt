#!/usr/bin/env bash
# Lembrete de estudo de japones, exibido na abertura do shell.
# Fica em silencio quando a sessao do dia ja foi cumprida.
# Para desativar: remova o bloco correspondente de ~/.config/fish/config.fish

ESTADO="$HOME/Documentos/facul/ai-job-search/progresso/estado.json"
[ -f "$ESTADO" ] || exit 0

python3 - "$ESTADO" <<'PY' 2>/dev/null
import json, sys, datetime

try:
    dados = json.load(open(sys.argv[1]))
    prog = dados["progresso"]
except Exception:
    sys.exit(0)

hoje = datetime.date.today()
ultima = prog.get("ultima_sessao")

# Sessao de hoje ja feita: nao incomoda.
if ultima == hoje.isoformat():
    sys.exit(0)

dia = prog.get("dia_do_plano", 0) + 1
streak = prog.get("streak_atual", 0)
faltam = (datetime.date(2027, 12, 5) - hoje).days

if ultima:
    atraso = (hoje - datetime.date.fromisoformat(ultima)).days
    if atraso >= 3:
        print(f"\033[33m🇯🇵 Japones: {atraso} dias sem sessao. Retomada e so revisao -> \033[1mclaude /estudo\033[0m")
        sys.exit(0)

print(f"\033[36m🇯🇵 Japones dia {dia} pendente · streak {streak} · {faltam} dias ate a prova -> \033[1mclaude /estudo\033[0m")
PY
