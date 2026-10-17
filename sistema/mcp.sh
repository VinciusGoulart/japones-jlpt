#!/bin/sh
# Lançador do servidor MCP do sistema de estudo (chamado pelo .mcp.json da raiz).
# Entra na pasta do sistema antes, para não depender do diretório de quem chamou.
cd "$(dirname "$0")" && exec .venv/bin/python -m japones.mcp_server
