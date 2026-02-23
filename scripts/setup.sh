#!/usr/bin/env bash
# scripts/setup.sh – Bootstrap the project on a fresh machine (dev or Pi).
#
# Usage:
#   ./scripts/setup.sh          # install runtime deps only
#   ./scripts/setup.sh --dev    # also install dev/test deps
#
# Requires: uv  (https://docs.astral.sh/uv/getting-started/installation/)

set -euo pipefail

DEV=false
for arg in "$@"; do
  [[ "$arg" == "--dev" ]] && DEV=true
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

# ── 1. Ensure uv is available ──────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
  echo "► uv not found – installing via official installer…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Make uv available in this session
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "► uv $(uv --version)"

# ── 2. Create / sync virtual environment ───────────────────────────────────
if $DEV; then
  echo "► Installing runtime + dev dependencies…"
  uv sync --extra dev
else
  echo "► Installing runtime dependencies…"
  uv sync
fi

# ── 3. Copy .env if missing ─────────────────────────────────────────────────
if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo "► Created .env from .env.example – fill in your secrets before running."
else
  echo "► .env already exists (skipping copy)"
fi

echo ""
echo "✓ Setup complete."
echo "  Activate venv : source .venv/bin/activate"
echo "  Run dev server: ./scripts/dev.sh"
echo "  Run migrations: ./scripts/migrate.sh"
