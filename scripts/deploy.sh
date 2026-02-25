#!/usr/bin/env bash
# scripts/deploy.sh – Deploy / update the service on the Raspberry Pi.
#
# Run this ON THE PI after pulling the latest code:
#
#   git pull origin main
#   ./scripts/deploy.sh
#
# Or call it remotely:
#
#   ssh pi@raspberry-pi "cd ~/goal-agent && git pull && ./scripts/deploy.sh"
#
# What it does:
#   1. Ensure uv is installed
#   2. Sync Python deps (runtime only)
#   3. Run Alembic migrations
#   4. Reload the systemd service (zero-downtime via systemd)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

SERVICE_NAME="goal-agent"
SYSTEMD_UNIT_SRC="$ROOT/systemd/${SERVICE_NAME}.service"
SYSTEMD_UNIT_DST="/etc/systemd/system/${SERVICE_NAME}.service"

# ── Colours ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "${GREEN}►${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
die()  { echo -e "${RED}✗${NC}  $*" >&2; exit 1; }

# ── 1. uv ──────────────────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
  step "Installing uv…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
step "uv $(uv --version)"

# ── 2. Install / sync deps ─────────────────────────────────────────────────
step "Syncing Python dependencies…"
uv sync --no-dev

# ── 3. Check .env ──────────────────────────────────────────────────────────
if [[ ! -f ".env" ]]; then
  warn ".env missing – copying from .env.example. Fill in your secrets!"
  cp .env.example .env
fi

# ── 4. Run migrations ──────────────────────────────────────────────────────
step "Running database migrations…"
uv run alembic upgrade head

# ── 5. Install / refresh systemd unit ─────────────────────────────────────
if [[ -f "$SYSTEMD_UNIT_SRC" ]]; then
  if [[ "$(id -u)" -eq 0 ]]; then
    step "Installing systemd service…"
    # Update WorkingDirectory and ExecStart to point to this directory
    sed "s|/home/pi/goal-agent|$ROOT|g" \
        "$SYSTEMD_UNIT_SRC" > "$SYSTEMD_UNIT_DST"
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
  else
    warn "Not running as root – skipping systemd unit install."
    warn "Run: sudo cp $SYSTEMD_UNIT_SRC $SYSTEMD_UNIT_DST && sudo systemctl daemon-reload"
  fi
fi

# ── 6. Restart / start the service ────────────────────────────────────────
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
  step "Reloading ${SERVICE_NAME}…"
  sudo systemctl reload-or-restart "$SERVICE_NAME"
elif systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
  step "Starting ${SERVICE_NAME}…"
  sudo systemctl start "$SERVICE_NAME"
else
  warn "Service not managed by systemd on this host. Start manually:"
  warn "  ./scripts/dev.sh     (dev mode)"
  warn "  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --loop uvloop"
fi

echo ""
echo -e "${GREEN}✓ Deploy complete.${NC}"
