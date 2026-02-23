#!/usr/bin/env bash
# scripts/dev.sh – Start the API server in development (hot-reload) mode.
#
# Usage:
#   ./scripts/dev.sh          # default: 0.0.0.0:8000
#   PORT=9000 ./scripts/dev.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "✗ Virtual environment not found. Run ./scripts/setup.sh first."
  exit 1
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "► Starting dev server at http://${HOST}:${PORT}  (hot-reload ON)"
echo "  API docs  : http://localhost:${PORT}/docs"
echo "  MCP tools : http://localhost:${PORT}/mcp"
echo ""

# Note: --workers 1 is required because APScheduler runs in-process.
# --reload is for development only; remove in production.
uv run uvicorn app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  --workers 1 \
  --reload \
  --reload-dir app
