# Deploying Goal Agent with OpenClaw Integration

This guide covers the complete setup of Goal Agent on a Raspberry Pi with OpenClaw plugin integration. It also serves as a reference for day-to-day deployment updates.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Raspberry Pi OS (Debian 12+) | aarch64 |
| Python 3.12 | via `uv` |
| [uv](https://docs.astral.sh/uv/) | installed by `setup.sh` |
| MariaDB | `sudo apt install mariadb-server` |
| Node.js ≥ 18 | `sudo apt install nodejs` |
| [OpenClaw](https://openclaw.ai) | installed at `~/.openclaw/` |
| Telegram bot tokens | best_pal bot + go_getter bot |
| Kimi API key | `sk-…` from Moonshot AI |
| GitHub PAT | for auto-committing reports |

---

## First-Time Setup

### 1. Clone and bootstrap

```bash
git clone https://github.com/rushwing/goal-agent.git
cd goal-agent
./scripts/setup.sh --dev        # installs uv, creates .venv, copies .env.example → .env
```

### 2. Configure `.env`

```bash
$EDITOR .env
```

Follow the step-by-step guide to obtain each value (bot tokens, API keys, chat IDs, etc.):

> **[docs/env-setup.md](env-setup.md)** — detailed instructions for every `.env` variable

`deploy.sh` will warn you at the end if any placeholder values remain unfilled.

### 3. Initialise the database

Creates the MariaDB database and user, then runs all Alembic migrations:

```bash
# Root with unix_socket auth (Raspberry Pi OS default — no password needed)
./scripts/db_init.sh

# Or if your root account has a password
./scripts/db_init.sh -p <root_password>
```

### 4. Install the systemd service (one-time, requires sudo)

`deploy.sh` skips this step when not running as root. Run it once manually:

```bash
ROOT=$(pwd)
USER=$(id -un)
GROUP=$(id -gn)
sudo bash -c "
  sed -e 's|/home/pi/goal-agent|$ROOT|g' \
      -e 's|User=pi|User=$USER|g' \
      -e 's|Group=pi|Group=$GROUP|g' \
      $ROOT/systemd/goal-agent.service > /etc/systemd/system/goal-agent.service
  systemctl daemon-reload
  systemctl enable goal-agent
"
```

### 5. Run the first deploy

```bash
./scripts/deploy.sh
```

This will:
1. Sync Python dependencies
2. Run any pending Alembic migrations
3. Build and install the OpenClaw plugin (see below)
4. Start the systemd service

---

## OpenClaw Plugin Integration

The plugin is built and installed automatically by `deploy.sh` (step 5). No manual steps are needed on subsequent deploys.

### What `deploy.sh` does

```
► Building OpenClaw plugin…        # npm install + npm run build (best-effort — failure does not abort deploy)
► Writing plugin config.json…      # seeded from APP_PORT + ADMIN_CHAT_IDS in .env (only if missing or .env is newer)
► Installing OpenClaw plugin…      # node ~/.openclaw/openclaw.mjs plugins install --link (non-fatal if already registered)
```

> **Note**: The build step is best-effort. If `npm install` or `npm run build` fails (e.g. due to network issues), a warning is printed and the service deploy continues normally.

### Plugin config (`config.json` vs entry config)

`deploy.sh` automatically writes `openclaw-plugin/config.json` the first time (or whenever `.env` is newer), seeded from your `.env`:

```json
{
  "apiBaseUrl": "http://127.0.0.1:<APP_PORT>/api/v1",
  "telegramChatId": "<first value in ADMIN_CHAT_IDS>",
  "hmacSecret": "<HMAC_SECRET value from .env>"
}
```

It also patches `~/.openclaw/openclaw.json` to set the entry config under `plugins.entries.openclaw-goal-agent.config`. OpenClaw passes this as `api.pluginConfig` when it calls `plugin.register(api)` — this is the **primary** config source. The `config.json` file is the **fallback** when `api.pluginConfig` is absent. It is gitignored and must not be committed.

`hmacSecret` is included when `HMAC_SECRET` is set in `.env`. It must match the server's `HMAC_SECRET` exactly — the plugin uses it to sign every request with `X-Request-Timestamp`, `X-Nonce`, and `X-Signature` headers.

**For multi-user setups**, override per-user via the entry config in `~/.openclaw/openclaw.json` (under `plugins.entries.openclaw-goal-agent.config`):

**Best Pal config** (parent — accesses wizard, plan, report, tracks tools):

```json
{
  "apiBaseUrl": "http://127.0.0.1:8000/api/v1",
  "telegramChatId": "111111111",
  "hmacSecret": "<your HMAC_SECRET>"
}
```

**Go Getter config** (child — accesses check-in tools):

```json
{
  "apiBaseUrl": "http://127.0.0.1:8000/api/v1",
  "telegramChatId": "222222222",
  "hmacSecret": "<your HMAC_SECRET>"
}
```

The `telegramChatId` is used as the `X-Telegram-Chat-Id` header, which the server uses to resolve the user's role (`admin`, `best_pal`, or `go_getter`).

### Verify the plugin is loaded

```bash
node ~/.openclaw/openclaw.mjs plugins list
```

Expected output includes `openclaw-goal-agent`.

### Available tools by role

| Role | Tools |
|------|-------|
| `admin` | add/update/remove/list go_getters & best_pals |
| `best_pal` / `admin` | create/update/delete targets, generate plans, wizard, reports, tracks |
| `go_getter` | list today/week tasks, checkin, skip, progress |

Full tool list: see [README.md → MCP Tools](../README.md#mcp-tools).

---

## Day-to-Day Deployment Updates

After every `git pull`:

```bash
git pull origin main
./scripts/deploy.sh
```

`deploy.sh` is fully idempotent — safe to re-run at any time:

| Step | Behaviour on re-run |
|------|-------------------|
| uv sync | no-op if deps unchanged |
| Alembic migrate | only runs unapplied migrations |
| OpenClaw plugin build | rebuilds from source (best-effort — failure is non-fatal) |
| plugin `config.json` | written only if missing or `.env` is newer |
| OpenClaw plugin install | re-registers (non-fatal if already registered) |
| systemd reload | `reload-or-restart` — brief or zero downtime |
| cron job | skips if already installed |

---

## Troubleshooting

### `ERROR 1698: Access denied for user 'root'`

Raspberry Pi OS MariaDB root uses unix_socket auth. `db_init.sh` handles this automatically — use it instead of running `mysql -u root` directly.

### `plugin manifest requires id`

Add `"id": "openclaw-goal-agent"` to `openclaw.plugin.json`. This is already present in the repo; ensure you've pulled the latest code and rebuilt (`npm run build`).

### `package.json missing openclaw.extensions`

OpenClaw 2026.1.30+ requires the `openclaw` field in `package.json`. Already present in the repo — ensure you've pulled latest.

### `Failed to load environment files: No such file or directory`

The systemd unit is using wrong paths (hardcoded for user `pi`). Re-run the one-time systemd install command in step 4 above.

### Service fails to start

```bash
journalctl -u goal-agent -n 50 --no-pager
```

Common causes: missing `.env`, database not running, wrong `DATABASE_URL`.

### Plugin not showing tools in OpenClaw

- Check the API is reachable: `curl http://127.0.0.1:8000/health`
- Check that `openclaw-plugin/config.json` exists (created by `deploy.sh`), or that `~/.openclaw/openclaw.json` has a valid `plugins.entries.openclaw-goal-agent.config` block
- Check the `telegramChatId` matches a registered user (`admin`, `best_pal`, or `go_getter`)

### `config.json` has wrong `telegramChatId`

`deploy.sh` seeds `config.json` with the first entry from `ADMIN_CHAT_IDS`. To use a different chat ID (e.g. for a go_getter user), edit the `plugins.entries.openclaw-goal-agent.config` block in `~/.openclaw/openclaw.json` for that profile — it takes precedence over `config.json`.
