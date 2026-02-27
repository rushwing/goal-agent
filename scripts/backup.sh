#!/usr/bin/env bash
# scripts/backup.sh – Backup MariaDB database and .env file.
#
# Usage:
#   ./scripts/backup.sh                    # creates timestamped backup in ./backups/
#   ./scripts/backup.sh /path/to/custom   # backup to custom directory
#
# Required env vars (must be set in .env):
#   DB_HOST, DB_NAME, DB_USER, DB_PASSWORD
#
# Output:
#   backups/goal-agent-YYYYMMDD-HHMMSS.sql.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

BACKUP_DIR="${1:-${ROOT}/backups}"

# Load env vars
if [[ -f ".env" ]]; then
    set -a
    source .env
    set +a
fi

# ── Validate required env vars ────────────────────────────────────────────────
: "${DB_HOST:?DB_HOST is required}"
: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/goal-agent-${TIMESTAMP}.sql.gz"

# ── Colours ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "${GREEN}►${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
die()  { echo -e "${RED}✗${NC}  $*" >&2; exit 1; }

# ── Prepare backup directory ────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

# ── Backup database ────────────────────────────────────────────────────────
# Use MYSQL_PWD env var to avoid password appearing in process list
step "Backing up database $DB_NAME..."
export MYSQL_PWD="$DB_PASSWORD"
if mysqldump -h"$DB_HOST" -u"$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    step "Database backed up to $BACKUP_FILE"
else
    die "Database backup failed"
fi
unset MYSQL_PWD

# ── Backup .env (full file, includes secrets) ───────────────────────────────
ENV_BACKUP="${BACKUP_DIR}/env-${TIMESTAMP}.tar.gz"
if [[ -f ".env" ]]; then
    tar -czf "$ENV_BACKUP" .env 2>/dev/null || true
    step "Env file backed up to $ENV_BACKUP"
fi

# ── Cleanup old backups (keep last 7 days) ────────────────────────────────
find "$BACKUP_DIR" -name "goal-agent-*.sql.gz" -mtime +7 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "env-*.tar.gz"        -mtime +7 -delete 2>/dev/null || true

# ── Report ─────────────────────────────────────────────────────────────────
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo ""
echo -e "${GREEN}✓ Backup complete: $BACKUP_FILE (${BACKUP_SIZE})${NC}"
