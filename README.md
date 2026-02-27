# Goal Agent

AI-powered goal and habit tracking agent. Generates personalized study plans using **Kimi 2.5** (Moonshot AI), tracks daily task completion with Duolingo-style streaks and XP, auto-commits progress reports to GitHub, and delivers notifications via Telegram. Designed to run on a **Raspberry Pi 5** as a lightweight home server.

---

## Architecture

```
[OpenClaw Best Pal Bot] ─┐                   ┌─ [Kimi 2.5 API]
[OpenClaw Go Getter Bot] ─┤                  │
                          ▼                  ▼
              [FastAPI REST :8000] ── [FastMCP /mcp]
                       │
              [Services Layer]
                ├─ plan_generator     (Kimi → structured JSON plan)
                ├─ praise_engine      (Kimi + 20+ offline templates)
                ├─ report_service     (daily / weekly / monthly Markdown)
                ├─ streak_service     (XP formula, streak, achievements)
                ├─ github_service     (PyGithub → private data repo)
                ├─ telegram_service   (httpx → Bot API)
                └─ scheduler_service  (APScheduler cron jobs)
                       │
              [MariaDB on Pi]
```

- **FastMCP** is mounted as an ASGI sub-app inside FastAPI — one process, one event loop.
- **APScheduler** runs in-process; a single uvicorn worker is required (`--workers 1`).
- **Role auth** is header-driven: `X-Telegram-Chat-Id` → `admin / best_pal / go_getter`.
- **OpenClaw** (TypeScript plugin) calls the FastAPI REST layer directly — it does not speak MCP natively.

---

## Features

| Stage | Status | Description |
|-------|--------|-------------|
| 1 – Foundation | ✅ | DB models, Alembic, CRUD, FastMCP + role auth, admin tools |
| 2 – Planning Engine | ✅ | AI plan generation (Kimi), GitHub auto-commit |
| 3 – Check-in System | ✅ | Streak / XP / badges, praise engine |
| 4 – Reports | ✅ | Daily / weekly / monthly Markdown reports, GitHub archival |
| 5 – Telegram & OpenClaw | ✅ | Scheduler jobs, Telegram DMs & group, TypeScript plugin |
| 6 – GoalGroup Wizard | ✅ | Guided multi-step GoalGroup + plan creation via OpenClaw conversation |
| 7 – Gamification+ | 🔜 | Sibling leaderboard, streak freeze, XP shop |
| 8 – Frontend | 🔜 | Jinja2 dashboard or React SPA |

---

## Collaboration / Issue Flow

- Human quick start (3-minute triage/routing guide): [`docs/issues/quick_start_for_humans.md`](docs/issues/quick_start_for_humans.md)
- Human-facing issue lifecycle and capability-based assignment guide: [`docs/issues/issue_flow.md`](docs/issues/issue_flow.md)
- Machine-readable LLM routing protocol: [`.github/LLM_ROUTING.md`](.github/LLM_ROUTING.md)

---

## Project Layout

```
goal-agent/
├── app/
│   ├── main.py                  # FastAPI app + FastMCP mount + lifespan
│   ├── config.py                # Pydantic BaseSettings (.env)
│   ├── database.py              # SQLAlchemy 2.0 async engine
│   ├── models/                  # 10 ORM models (utf8mb4)
│   ├── schemas/                 # Pydantic v2 request/response schemas
│   ├── crud/                    # Generic CRUDBase + 8 specific modules
│   ├── api/v1/                  # FastAPI REST routers
│   ├── mcp/                     # FastMCP server + auth + 36 tools (6 groups)
│   └── services/                # LLM, streak, praise, reports, GitHub, Telegram, scheduler
├── alembic/                     # Async-aware migrations
├── openclaw-plugin/             # TypeScript OpenClaw plugin (axios)
├── scripts/                     # Dev, test, lint, migrate, deploy
├── systemd/                     # systemd unit + MariaDB tuning config
├── tests/                       # pytest (unit + integration, SQLite in-memory)
├── Dockerfile                   # Multi-stage build (uv + slim runtime)
├── docker-compose.yml           # API + MariaDB + one-shot migrate service
└── pyproject.toml               # uv / hatchling / ruff / pytest config
```

---

## Quick Start

### Prerequisites

- Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/)
- MariaDB / MySQL (or use Docker Compose)
- Telegram bot tokens (best_pal + go_getter), Kimi API key, GitHub PAT

### 1 – Bootstrap

```bash
git clone https://github.com/your-org/goal-agent.git
cd goal-agent
./scripts/setup.sh --dev        # installs uv, creates .venv, copies .env
```

Edit `.env` with your secrets (see [Environment Variables](#environment-variables)).

### 2 – Database

```bash
# Native MariaDB
./scripts/migrate.sh            # alembic upgrade head

# Or Docker Compose (starts MariaDB + runs migrations)
docker compose --profile migrate up migrate
```

### 3 – Run

```bash
# Development (hot-reload)
./scripts/dev.sh

# Production (single worker required for APScheduler)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --loop uvloop
```

API docs: `http://localhost:8000/docs`
MCP tools: `http://localhost:8000/mcp`

---

## Scripts

| Script | Purpose |
|--------|---------|
| `./scripts/setup.sh [--dev]` | Install uv, sync deps, copy `.env` |
| `./scripts/dev.sh` | Hot-reload dev server |
| `./scripts/migrate.sh [cmd]` | Alembic wrapper (default: `upgrade head`) |
| `./scripts/test.sh [--cov]` | Run pytest (SQLite in-memory, no MariaDB needed) |
| `./scripts/lint.sh [--fix]` | ruff check + format |
| `./scripts/deploy.sh` | Full Pi deploy: sync → migrate → `systemctl reload` |

---

## Deployment on Raspberry Pi 5

### Native (recommended)

```bash
# On the Pi, after git pull:
./scripts/deploy.sh
```

This syncs deps, runs migrations, installs the systemd unit, and reloads the service. MariaDB tuning is in `systemd/99-planner.cnf`:

```ini
innodb_buffer_pool_size = 128M
max_connections         = 30
character-set-server    = utf8mb4
collation-server        = utf8mb4_unicode_ci
```

### Docker Compose (alternative)

```bash
cp .env.example .env            # fill in secrets
docker compose up -d            # starts api + db
docker compose --profile migrate up migrate   # run migrations once
docker compose logs -f api      # follow logs
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `mysql+aiomysql://user:pass@host:3306/db` |
| `KIMI_API_KEY` | Moonshot API key (`sk-…`) |
| `KIMI_BASE_URL` | `https://api.moonshot.cn/v1` |
| `KIMI_MODEL_SHORT` | `moonshot-v1-8k` (praise / short tasks) |
| `KIMI_MODEL_LONG` | `moonshot-v1-32k` (plan generation) |
| `TELEGRAM_BEST_PAL_BOT_TOKEN` | Bot token for best pal DMs + group |
| `TELEGRAM_GO_GETTER_BOT_TOKEN` | Bot token for go getter DMs |
| `TELEGRAM_GROUP_CHAT_ID` | Family Telegram group chat ID |
| `GITHUB_PAT` | Personal access token for data repo |
| `GITHUB_DATA_REPO` | `username/study-data-private` |
| `ADMIN_CHAT_IDS` | Comma-separated bootstrap admin chat IDs |

Copy `.env.example` → `.env` to get started.

---

## MCP Tools

All tools require the `X-Telegram-Chat-Id` header for role resolution.

### Admin tools (`admin` role)
`add_go_getter` · `update_go_getter` · `remove_go_getter` · `list_go_getters`
`add_best_pal` · `update_best_pal` · `remove_best_pal` · `list_best_pals`

### Plan tools (`best_pal / admin` role)
`create_target` · `update_target` · `delete_target` · `list_targets`
`generate_plan` · `update_plan` · `delete_plan` · `list_plans` · `get_plan_detail`

### Check-in tools (`go_getter` role)
`list_today_tasks` · `list_week_tasks` · `checkin_task` · `skip_task` · `get_go_getter_progress`

### Report tools (`best_pal / admin`; go_getter for own)
`generate_daily_report` · `generate_weekly_report` · `generate_monthly_report` · `list_reports`

### Wizard tools (`best_pal / admin` role)
`start_goal_group_wizard` · `get_wizard_status` · `set_wizard_scope`
`set_wizard_targets` · `set_wizard_constraints` · `adjust_wizard`
`confirm_goal_group` · `cancel_goal_group_wizard`

### Track tools (`all authenticated roles`)
`list_track_categories` · `list_track_subcategories`

---

## XP & Streak System

```
xp = base_xp × streak_multiplier × mood_bonus

streak_multiplier:  days 1-2 → 1.0 · days 3-6 → 1.2 · days 7-13 → 1.5 · days 14+ → 2.0
mood_bonus:         1 → 0.8 · 2 → 0.9 · 3 → 1.0 · 4 → 1.1 · 5 → 1.2
```

### Achievement Badges

| Badge | Icon | Trigger | XP Bonus |
|-------|------|---------|----------|
| First Step! | 🌟 | First task checked in | +10 |
| 3-Day Streak! | 🔥 | 3 consecutive study days | +15 |
| Week Warrior! | 🦁 | 7 consecutive study days | +30 |
| Fortnight Champion! | 🏆 | 14 consecutive study days | +75 |
| Monthly Master! | 👑 | 30 consecutive study days | +200 |
| 50 XP Club! | ⭐ | Earn 50 total XP | +5 |
| Century Scholar! | 💯 | Earn 100 total XP | +10 |
| XP Legend! | 🎖️ | Earn 500 total XP | +50 |
| Weekend Warrior! | 🏄 | Check in on Sat & Sun | +20 |

---

## Scheduler Jobs

| Time | Job |
|------|-----|
| 07:30 daily | Send today's task list DM to each active go getter |
| 21:00 daily | Evening reminder for unchecked tasks + generate daily report + post summary to Telegram group |
| Sunday 20:00 | Generate weekly report + post summary to Telegram group |
| 1st of month 08:00 | Generate monthly report + post summary to Telegram group |

---

## OpenClaw Plugin

The TypeScript plugin lives in `openclaw-plugin/`. It calls FastAPI REST endpoints directly (OpenClaw does not speak MCP natively).

```bash
cd openclaw-plugin
npm install
npm run build
```

Configure via environment variable:

```json
PLUGIN_CONFIG='{"apiBaseUrl":"http://raspberry-pi-ip:8000/api/v1","telegramChatId":"123456789"}'
```

Optional HMAC signing (production):

```json
PLUGIN_CONFIG='{"apiBaseUrl":"...","telegramChatId":"...","hmacSecret":"your-shared-secret"}'
```

Two configs are typical — one with a best pal's chat ID (accesses wizard, plan, report, tracks tools), one with a go getter's (accesses check-in tools). The server resolves the role from `X-Telegram-Chat-Id` automatically.

### Available tool groups in the plugin

| Group | File | Tools |
|-------|------|-------|
| Admin | `admin.tools.ts` | add/update/remove/list go_getters & best_pals |
| Plan | `plan.tools.ts` | create/update/delete/list targets & plans |
| Check-in | `checkin.tools.ts` | today tasks, checkin, skip, progress |
| Report | `report.tools.ts` | daily / weekly / monthly reports |
| **Wizard** | `wizard.tools.ts` | guided GoalGroup creation (8 steps) |
| **Tracks** | `tracks.tools.ts` | list categories & subcategories |

### GoalGroup Wizard conversation flow (BestPal)

```
list_track_categories          ← discover subcategory IDs
create_target (subcategory_id) ← add learning goals for go_getter
start_goal_group_wizard        ← begin guided creation
set_wizard_scope               ← title + date range (≥ 7 days)
set_wizard_targets             ← select which targets to include
set_wizard_constraints         ← daily minutes per target (triggers AI plan gen, ~10–30 s/target)
get_wizard_status              ← read feasibility_passed + blockers/warnings
adjust_wizard                  ← fix blockers (re-generates plans)
confirm_goal_group             ← create GoalGroup + activate plans
```

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Web framework | FastAPI 0.115+ |
| MCP server | FastMCP 2.0+ |
| ORM | SQLAlchemy 2.0 async |
| DB driver | aiomysql |
| Migrations | Alembic 1.15+ (async env) |
| Validation | Pydantic v2 |
| LLM client | openai SDK (Kimi-compatible) |
| HTTP client | httpx (async) |
| Scheduler | APScheduler 3.10+ |
| GitHub | PyGithub (ThreadPoolExecutor) |
| Python tooling | uv |
| Linter | ruff |
| Tests | pytest + pytest-asyncio + aiosqlite |
| Deployment | uvicorn + uvloop, systemd, Docker Compose |
