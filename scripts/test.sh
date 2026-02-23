#!/usr/bin/env bash
# scripts/test.sh – Run the test suite (uses in-memory SQLite, no MariaDB needed).
#
# Usage:
#   ./scripts/test.sh                      # all tests
#   ./scripts/test.sh tests/unit/          # unit tests only
#   ./scripts/test.sh -k test_streak       # filter by name
#   ./scripts/test.sh --cov                # with coverage report

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "✗ Virtual environment not found. Run ./scripts/setup.sh --dev first."
  exit 1
fi

# Collect extra args (path filter, -k, --cov, etc.)
EXTRA_ARGS=("$@")

# Enable coverage if --cov flag passed
COV_ARGS=()
for arg in "${EXTRA_ARGS[@]}"; do
  if [[ "$arg" == "--cov" ]]; then
    COV_ARGS=(--cov=app --cov-report=term-missing --cov-report=html:htmlcov)
    # Remove --cov from EXTRA_ARGS so pytest doesn't see a duplicate
    EXTRA_ARGS=("${EXTRA_ARGS[@]/--cov/}")
  fi
done

echo "► Running tests…"
uv run pytest "${COV_ARGS[@]}" "${EXTRA_ARGS[@]}"
