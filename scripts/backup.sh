#!/usr/bin/env bash
# scripts/backup.sh – Backup MariaDB database and .env file.
#
# Usage:
#   ./scripts/backup.sh                    # creates timestamped backup in ./backups/
#   ./scripts/backup.sh /path/to/custom     # backup to custom directory
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

DB_USER="${DB_USER:-planner}"
DB_PASS="${DB_PASSWORD:-plannerpass}"
DB_NAME="${DB_NAME:-vocation_planner}"
DB_HOST="${DB_HOST:-localhost}"

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
step "Backing up database $DB_NAME..."
if mysqldump -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    step "Database backed up to $BACKUP_FILE"
else
    die "Database backup failed"
fi

# ── Backup .env (exclude secrets in production) ─────────────────────────────
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
