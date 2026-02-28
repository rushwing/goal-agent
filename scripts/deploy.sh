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

# Load .env into the current shell so subsequent steps can read its values
# (e.g. APP_PORT, ADMIN_CHAT_IDS for plugin config.json generation).
# shellcheck disable=SC1091
set -o allexport
source .env
set +o allexport

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
  # P2 fix: build is best-effort — network/npm failure must not abort service deploy
  step "Building OpenClaw plugin…"
  if (cd "$PLUGIN_DIR" && npm install --silent && npm run build --silent); then

    # P1 fix: write config.json so plugin works without manual PLUGIN_CONFIG setup.
    # apiBaseUrl is derived from .env; telegramChatId seeds from ADMIN_CHAT_IDS
    # (first entry) and can be overridden per-user via OpenClaw's PLUGIN_CONFIG.
    APP_PORT="${APP_PORT:-8000}"
    ADMIN_CHAT_ID="${ADMIN_CHAT_IDS%%,*}"   # first entry only

    # ── Write config.json as fallback (used when PLUGIN_CONFIG env var absent) ─
    CONFIG_FILE="$PLUGIN_DIR/config.json"
    if [[ ! -f "$CONFIG_FILE" ]] || [[ ".env" -nt "$CONFIG_FILE" ]]; then
      step "Writing plugin config.json (fallback)…"
      cat > "$CONFIG_FILE" <<JSON
{
  "apiBaseUrl": "http://localhost:${APP_PORT}/api/v1",
  "telegramChatId": "${ADMIN_CHAT_ID}"
}
JSON
    fi

    # ── Clean up any prior extension registrations (copy or symlink) ────────────
    # OpenClaw scans ~/.openclaw/extensions/ AND plugins.load.paths at startup.
    # If the plugin appears in BOTH locations it loads twice → 36 tool-name
    # conflicts → gateway crash.  Remove both possible extension paths so the
    # plugin is loaded only from load.paths (the source tree).
    rm -rf "$HOME/.openclaw/extensions/goal-agent"           # legacy name
    rm -rf "$HOME/.openclaw/extensions/openclaw-goal-agent"  # copy or --link symlink

    # ── Patch openclaw.json directly (no CLI install) ─────────────────────────
    # OpenClaw plugin loading rules:
    #   load.paths  → actually loads the plugin JS file
    #   allow       → gates whether the plugin is active; MUST be present or
    #                 the entry is "disabled (not in allowlist)" warning
    #   installs    → if plugin is in BOTH allow AND installs, OpenClaw loads
    #                 it a second time → 36 tool-name conflicts → gateway crash
    #
    # Target state:
    #   load.paths: [plugin_dir]                           ← file load source
    #   allow:      [..., "openclaw-goal-agent"]           ← must be present
    #   installs:   (no openclaw-goal-agent entry)         ← removed; prevents double load
    #   entries:    { openclaw-goal-agent: { enabled, config } }
    #
    # Patcher tasks:
    #   1. Ensure plugin_dir is in load.paths
    #   2. Ensure openclaw-goal-agent is in allow
    #   3. Remove openclaw-goal-agent from installs (allow + installs = double load)
    #   4. Set entry config (apiBaseUrl + telegramChatId → injected as PLUGIN_CONFIG)
    OPENCLAW_JSON="$HOME/.openclaw/openclaw.json"
    if [[ -f "$OPENCLAW_JSON" ]]; then
      step "Patching openclaw.json plugin registration…"
      python3 - "$OPENCLAW_JSON" "${APP_PORT}" "${ADMIN_CHAT_ID}" "${PLUGIN_DIR}" <<'PYEOF'
import json, sys
path, port, chat_id, plugin_dir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(path) as f:
    cfg = json.load(f)

plugins = cfg.setdefault("plugins", {})

# 1. Ensure plugin_dir is in load.paths (actual file-load mechanism)
load_paths = plugins.setdefault("load", {}).setdefault("paths", [])
if plugin_dir not in load_paths:
    load_paths.append(plugin_dir)
    print(f"  added {plugin_dir} to plugins.load.paths")

# 2. Ensure openclaw-goal-agent is in allow (required or entry is "disabled")
allow = plugins.setdefault("allow", [])
if "openclaw-goal-agent" not in allow:
    allow.append("openclaw-goal-agent")
    print("  added openclaw-goal-agent to plugins.allow")

# 3. Remove from installs — allow + installs triggers a second load (36 conflicts)
installs = plugins.get("installs", {})
if "openclaw-goal-agent" in installs:
    del installs["openclaw-goal-agent"]
    plugins["installs"] = installs
    print("  removed openclaw-goal-agent from plugins.installs (prevents double load)")

# 4. Set entry config (injected as PLUGIN_CONFIG at runtime)
entry = plugins.setdefault("entries", {}).setdefault("openclaw-goal-agent", {})
entry["enabled"] = True
entry["config"] = {
    "apiBaseUrl": f"http://localhost:{port}/api/v1",
    "telegramChatId": chat_id,
}

with open(path, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"  apiBaseUrl=http://localhost:{port}/api/v1  telegramChatId={chat_id}")
PYEOF
    else
      warn "~/.openclaw/openclaw.json not found — skipping openclaw.json patch."
      warn "Restart OpenClaw gateway after deploy to pick up the built plugin."
    fi
  else
    warn "OpenClaw plugin build failed — skipping plugin install. Service deploy continues."
  fi
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

# ── Post-deploy: warn if .env still contains placeholder values ─────────────
_has_placeholder() {
  # Match exact placeholder values from .env.example.
  # Anchored patterns (=$) prevent false positives on key names that contain
  # the substring (e.g. DB_PASSWORD=real_secret must not trigger =password$).
  grep -qE \
    'sk-your-key-here|123456:ABCdef|789012:GHIjkl|ghp_your_token_here|change-me|=password$|://[^:]+:password@|=-1001234567890$' \
    .env 2>/dev/null
}
if _has_placeholder; then
  echo ""
  warn "⚠  .env still contains placeholder values."
  warn "   Follow the setup guide to fill in your secrets:"
  warn "   docs/env-setup.md"
fi
