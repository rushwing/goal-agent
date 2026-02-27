#!/usr/bin/env bash
# scripts/db_init.sh – First-time MariaDB database and user setup.
#
# Creates the application database and user then runs Alembic migrations.
# Must be able to connect to MariaDB as root (or another admin account).
#
# Usage:
#   ./scripts/db_init.sh                         # root with socket auth (no password)
#   ./scripts/db_init.sh -p <root_password>      # root with password
#   MYSQL_ROOT_PASSWORD=<pw> ./scripts/db_init.sh
#   ./scripts/db_init.sh --skip-migrate          # skip Alembic step
#
# App DB credentials are read from .env:
#   Preferred  – DATABASE_URL (mysql+aiomysql://user:pw@host:port/db) — always used when present
#   Fallback   – individual vars: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
#
# Idempotent: safe to re-run (CREATE IF NOT EXISTS, ALTER USER for password sync).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "${GREEN}►${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
die()  { echo -e "${RED}✗${NC}  $*" >&2; exit 1; }

# ── Parse CLI args ────────────────────────────────────────────────────────────
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"
SKIP_MIGRATE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--root-password) MYSQL_ROOT_PASSWORD="$2"; shift 2 ;;
    --skip-migrate)     SKIP_MIGRATE=true;         shift   ;;
    -h|--help)          sed -n '2,15p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) die "Unknown argument: $1  (use --help for usage)" ;;
  esac
done

# ── Load .env ────────────────────────────────────────────────────────────────
if [[ -f ".env" ]]; then
  set -a; source .env; set +a
else
  warn ".env not found – falling back to .env.example defaults"
  if [[ -f ".env.example" ]]; then
    set -a; source .env.example; set +a
  fi
fi

# ── Resolve DB credentials ────────────────────────────────────────────────────
# DATABASE_URL is the canonical DSN used by the app and Alembic; always parse
# it when present so the script provisions exactly the DB the app will connect
# to.  DB_* vars are only used as a fallback when DATABASE_URL is absent.
if [[ -n "${DATABASE_URL:-}" ]]; then
  _rest="${DATABASE_URL#*://}"        # strip scheme (mysql+aiomysql://)
  DB_USER="${_rest%%:*}"
  _rest="${_rest#*:}"
  DB_PASSWORD="${_rest%%@*}"
  _rest="${_rest#*@}"
  DB_HOST="${_rest%%:*}"
  _rest="${_rest#*:}"
  DB_PORT="${_rest%%/*}"
  DB_NAME="${_rest#*/}"
  DB_NAME="${DB_NAME%%\?*}"           # strip any query params
elif [[ -n "${DB_HOST:-}" ]]; then
  : # use DB_* vars sourced from .env as-is
else
  die "No DB credentials found. Set DATABASE_URL (or DB_HOST/DB_NAME/DB_USER/DB_PASSWORD) in .env"
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
: "${DB_NAME:?DB_NAME not set. Check DATABASE_URL in .env}"
: "${DB_USER:?DB_USER not set. Check DATABASE_URL in .env}"
: "${DB_PASSWORD:?DB_PASSWORD not set. Check DATABASE_URL in .env}"

# ── Verify mysql client is available ─────────────────────────────────────────
if ! command -v mysql &>/dev/null; then
  die "mysql client not found. Install it first:  apt install mariadb-client"
fi

# ── Prepare root connection ───────────────────────────────────────────────────
# Debian/Raspberry Pi OS: the MariaDB root account uses unix_socket auth by
# default; TCP connections (forced by -h hostname) are always rejected unless a
# password is set.  When no root password is supplied and the target host is
# localhost we therefore use `sudo mysql` (socket auth) instead.
if [[ -n "$MYSQL_ROOT_PASSWORD" ]]; then
  MYSQL_CMD=(mysql -h "$DB_HOST" -P "$DB_PORT" -u root)
  export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"
elif [[ "$DB_HOST" == "localhost" || "$DB_HOST" == "127.0.0.1" ]]; then
  MYSQL_CMD=(sudo mysql)
  warn "No root password supplied — using 'sudo mysql' (unix_socket auth)."
  warn "You may be prompted for your sudo password."
else
  MYSQL_CMD=(mysql -h "$DB_HOST" -P "$DB_PORT" -u root)
fi

echo ""
step "Initialising MariaDB for goal-agent"
echo "    host     : ${DB_HOST}:${DB_PORT}"
echo "    database : ${DB_NAME}"
echo "    app user : ${DB_USER}"
echo ""

# ── Create database + user ────────────────────────────────────────────────────
step "Creating database and user…"
"${MYSQL_CMD[@]}" <<SQL
-- Database
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- App user (allow both localhost and remote connections)
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'%'         IDENTIFIED BY '${DB_PASSWORD}';

-- Sync password in case user already existed with a different one
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER '${DB_USER}'@'%'         IDENTIFIED BY '${DB_PASSWORD}';

-- Permissions
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'%';
FLUSH PRIVILEGES;
SQL

unset MYSQL_PWD
step "Database and user ready."

# ── Run migrations ────────────────────────────────────────────────────────────
if [[ "$SKIP_MIGRATE" == "true" ]]; then
  warn "Skipping migrations (--skip-migrate)."
else
  if [[ ! -f ".venv/bin/activate" ]]; then
    die "Virtual environment not found. Run ./scripts/setup.sh first."
  fi
  step "Running Alembic migrations…"
  uv run alembic upgrade head
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}✓ DB init complete.${NC} '${DB_NAME}' is ready."
echo ""
echo "Next steps:"
echo "  ./scripts/dev.sh    — start the development server"
echo "  ./scripts/test.sh   — run the test suite (uses SQLite, no DB needed)"
