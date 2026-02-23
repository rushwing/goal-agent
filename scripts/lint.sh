#!/usr/bin/env bash
# scripts/lint.sh – Run ruff linter and formatter check.
#
# Usage:
#   ./scripts/lint.sh          # check only (exit 1 on issues)
#   ./scripts/lint.sh --fix    # auto-fix what ruff can

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

FIX=false
for arg in "$@"; do
  [[ "$arg" == "--fix" ]] && FIX=true
done

if $FIX; then
  echo "► ruff check --fix …"
  uv run ruff check --fix app tests alembic
  echo "► ruff format …"
  uv run ruff format app tests alembic
else
  echo "► ruff check …"
  uv run ruff check app tests alembic
  echo "► ruff format --check …"
  uv run ruff format --check app tests alembic
fi

echo "✓ Lint OK."
