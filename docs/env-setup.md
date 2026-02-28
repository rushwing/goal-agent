# Filling in `.env` — Step-by-Step Guide

After running `./scripts/setup.sh --dev`, a `.env` file is created from `.env.example` **only if it does not already exist** — re-running setup or deploy will never overwrite a filled-in `.env`.
Fill in each section below before starting the service.

---

## 1. Database

```env
DATABASE_URL=mysql+aiomysql://planner:yourpassword@localhost:3306/goal_agent
DB_HOST=localhost
DB_PORT=3306
DB_NAME=goal_agent
DB_USER=planner
DB_PASSWORD=yourpassword
```

`DB_*` vars must match the credentials embedded in `DATABASE_URL`.
`db_init.sh` creates the MariaDB database and user using these values — run it once after editing:

```bash
./scripts/db_init.sh          # socket auth (no root password)
./scripts/db_init.sh -p <pw>  # or with root password
```

---

## 2. Kimi AI (Moonshot)

```env
KIMI_API_KEY=sk-...
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL_SHORT=moonshot-v1-8k
KIMI_MODEL_LONG=moonshot-v1-32k
```

Get your API key at [platform.moonshot.cn](https://platform.moonshot.cn). Leave `KIMI_BASE_URL` and model names as-is unless you need a different endpoint.

---

## 3. HMAC request signing (generate once)

```env
HMAC_SECRET=change-me-to-a-random-secret
```

Used to sign requests between the OpenClaw plugin and the API. Generate a random secret once and keep it:

```bash
openssl rand -hex 32
```

Paste the output as the value. Set the **same value** in the OpenClaw `PLUGIN_CONFIG` if you use HMAC signing:

```json
{ "apiBaseUrl": "...", "telegramChatId": "...", "hmacSecret": "your-secret-here" }
```

Leave `HMAC_SECRET` blank or unset to disable signing (fine for a local Pi with no external access).

---

## 4. Telegram Bots

```env
TELEGRAM_BEST_PAL_BOT_TOKEN=123456:ABCdef...
TELEGRAM_GO_GETTER_BOT_TOKEN=789012:GHIjkl...
TELEGRAM_GROUP_CHAT_ID=-1001234567890
```

### Create two bots with BotFather

1. Open Telegram → search `@BotFather` → `/newbot`
2. Follow prompts; copy the token (format `123456:ABCxyz…`)
3. Create one bot for **Best Pal** (parent) and one for **Go Getter** (child)

### Get the group chat ID

1. Add both bots to your family Telegram group
2. Send a message in the group, then open:
   `https://api.telegram.org/bot<BEST_PAL_BOT_TOKEN>/getUpdates`
3. Find `"chat":{"id":-100xxxxxxxxxx}` — that negative number is `TELEGRAM_GROUP_CHAT_ID`

### Get individual chat IDs (for `ADMIN_CHAT_IDS`)

1. Start a conversation with the Best Pal bot (send `/start`)
2. Open: `https://api.telegram.org/bot<BEST_PAL_BOT_TOKEN>/getUpdates`
3. Find `"from":{"id":xxxxxxxxx}` — that is your personal chat ID

---

## 5. GitHub (auto-committing reports)

```env
GITHUB_PAT=ghp_...
GITHUB_DATA_REPO=username/goal-agent-data
GITHUB_COMMITTER_NAME="Goal Agent Bot"
GITHUB_COMMITTER_EMAIL=bot@example.com
```

1. Create a **private** GitHub repo (e.g. `username/goal-agent-data`) to store plans and reports
2. Generate a Personal Access Token at [github.com/settings/tokens](https://github.com/settings/tokens):
   - Scope: `repo` (full control of private repositories)
3. Paste token as `GITHUB_PAT`
4. Set `GITHUB_DATA_REPO` to `username/your-repo-name`

---

## 6. App settings

```env
APP_SECRET_KEY=change-me-in-production
APP_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000
```

- `APP_SECRET_KEY`: used for session signing — generate with `openssl rand -hex 32`
- `APP_PORT`: default `8000`; change only if you need a different port
- `APP_DEBUG`: set `true` for dev, `false` for production

---

## 7. Admin bootstrap

```env
ADMIN_CHAT_IDS=123456789
```

Your personal Telegram chat ID (from step 4). This is used to:
- Seed the first admin account in the database
- Pre-fill `telegramChatId` in `openclaw-plugin/config.json` during `deploy.sh`

Multiple admins: comma-separated, e.g. `111111111,222222222`.

---

## Verification

After filling in `.env`, run:

```bash
./scripts/deploy.sh
```

If any placeholders remain, `deploy.sh` will warn you at the end.

To check the service is running:

```bash
journalctl -u goal-agent -n 20 --no-pager
curl http://localhost:8000/health
```
