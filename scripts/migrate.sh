#!/usr/bin/env bash
# scripts/migrate.sh – Run Alembic database migrations.
#
# Usage:
#   ./scripts/migrate.sh               # upgrade to head
#   ./scripts/migrate.sh downgrade -1  # pass any alembic sub-command + args
#   ./scripts/migrate.sh current
#   ./scripts/migrate.sh history

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "✗ Virtual environment not found. Run ./scripts/setup.sh first."
  exit 1
fi

if [[ ! -f ".env" ]]; then
  echo "✗ .env file missing. Copy .env.example and fill in DATABASE_URL."
  exit 1
fi

SUBCOMMAND="${1:-upgrade}"
ARGS="${@:2}"

if [[ "$SUBCOMMAND" == "upgrade" && -z "$ARGS" ]]; then
  ARGS="head"
fi

echo "► alembic $SUBCOMMAND $ARGS"
uv run alembic $SUBCOMMAND $ARGS

echo "✓ Migration complete."
