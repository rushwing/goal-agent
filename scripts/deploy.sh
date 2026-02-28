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
#   4. Build and install OpenClaw plugin (if openclaw + node are present)
#   5. Reload the systemd service (zero-downtime via systemd)

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

# ── 5. Build and install OpenClaw plugin ───────────────────────────────────
PLUGIN_DIR="$ROOT/openclaw-plugin"
OPENCLAW_MJS="$HOME/.openclaw/openclaw.mjs"

if [[ ! -d "$PLUGIN_DIR" ]]; then
  warn "openclaw-plugin directory not found – skipping plugin install."
elif ! command -v node &>/dev/null; then
  warn "node not found – skipping OpenClaw plugin install."
elif [[ ! -f "$OPENCLAW_MJS" ]]; then
  warn "OpenClaw not found at $OPENCLAW_MJS – skipping plugin install."
else
  step "Building OpenClaw plugin…"
  (cd "$PLUGIN_DIR" && npm install --silent && npm run build --silent)

  step "Installing OpenClaw plugin (openclaw-goal-agent)…"
  # --link is idempotent on update; suppress non-zero exit so a
  # "already installed" error from OpenClaw doesn't abort the deploy
  node "$OPENCLAW_MJS" plugins install --link "$PLUGIN_DIR" \
    || warn "OpenClaw plugin install returned non-zero (may already be registered) — continuing."
fi

# ── 6. Install / refresh systemd unit ─────────────────────────────────────
if [[ -f "$SYSTEMD_UNIT_SRC" ]]; then
  CURRENT_USER="$(id -un)"
  CURRENT_GROUP="$(id -gn)"
  _install_unit() {
    sed -e "s|/home/pi/goal-agent|$ROOT|g" \
        -e "s|User=pi|User=$CURRENT_USER|g" \
        -e "s|Group=pi|Group=$CURRENT_GROUP|g" \
        "$SYSTEMD_UNIT_SRC" > "$SYSTEMD_UNIT_DST"
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
  }
  if [[ "$(id -u)" -eq 0 ]]; then
    step "Installing systemd service…"
    _install_unit
  else
    warn "Not running as root – skipping systemd unit install."
    warn "Run the following to install (substitutes correct user/paths):"
    warn "  sudo bash -c \"sed -e 's|/home/pi/goal-agent|$ROOT|g' -e 's|User=pi|User=$CURRENT_USER|g' -e 's|Group=pi|Group=$CURRENT_GROUP|g' $SYSTEMD_UNIT_SRC > $SYSTEMD_UNIT_DST && systemctl daemon-reload && systemctl enable $SERVICE_NAME\""
  fi
fi

# ── 7. Restart / start the service ────────────────────────────────────────
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

# ── 8. Setup cron jobs ──────────────────────────────────────────────────────
step "Setting up cron jobs…"

# Detect uv binary (supports system-wide or user-local installation)
UV_BIN=$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")
BACKUP_CRON="0 3 * * * cd $ROOT && $UV_BIN run $ROOT/scripts/backup.sh >> $ROOT/logs/backup.log 2>&1"
CRON_MARKER="# goal-agent-backup"

# Create logs directory
mkdir -p "$ROOT/logs"

# Check if cron job already exists (by marker)
if crontab -l 2>/dev/null | grep -qF "$CRON_MARKER"; then
    step "Backup cron job already exists, skipping"
else
    # Add marker + cron job to user crontab
    (crontab -l 2>/dev/null || true; echo "$CRON_MARKER"; echo "$BACKUP_CRON") | crontab -
    step "Cron job installed: daily backup at 03:00"
fi

echo ""
echo -e "${GREEN}✓ Deploy complete.${NC}"
