# Goal Agent – Feature Stages

## Stage 1: Foundation (Critical)
- [x] Project setup (pyproject.toml, .env.example)
- [x] SQLAlchemy 2.0 async models (all 10 tables)
- [x] Alembic async migrations
- [x] Generic CRUD base + individual CRUD modules
- [x] FastMCP server with role-based auth (X-Telegram-Chat-Id)
- [x] Admin MCP tools: add/update/remove/list go_getters & best_pals
- [x] FastAPI main app + FastMCP mount (single process)

## Stage 2: Planning Engine (Critical)
- [x] Target CRUD (create_target, update_target, delete_target, list_targets)
- [x] `create_target` accepts optional `subcategory_id` for track taxonomy linkage
- [x] Kimi AI plan generation (generate_plan → structured JSON)
- [x] Milestone + task DB persistence
- [x] GitHub auto-commit of generated plans (Markdown)
- [x] Plan MCP tools: create_target, generate_plan, update_plan, list_plans, get_plan_detail

## Stage 3: Check-in System (Critical)
- [x] Task check-in: mood score, duration, notes
- [x] Streak service: XP formula, streak_multiplier, mood_bonus
- [x] Achievement unlocking (first_checkin, streak_3/7/14/30, xp milestones)
- [x] Praise engine: LLM + 20+ offline fallback templates
- [x] Check-in MCP tools: list_today_tasks, list_week_tasks, checkin_task, skip_task, get_go_getter_progress

## Stage 4: Reports (High)
- [x] Daily report (Markdown, GitHub commit)
- [x] Weekly report (Markdown, GitHub commit)
- [x] Monthly report (Markdown, GitHub commit)
- [x] Report MCP tools: generate_daily/weekly/monthly_report, list_reports

## Stage 5: Telegram & OpenClaw Integration (High)
- [x] Telegram service (httpx async, best_pal + go_getter bots)
- [x] APScheduler cron jobs (morning tasks, evening reminders, weekly/monthly/daily reports)
- [x] Daily report summary now posted to Telegram group (matches weekly/monthly behaviour)
- [x] OpenClaw TypeScript plugin (axios HTTP client, X-Telegram-Chat-Id injection, optional HMAC signing)
- [x] Group notifications for daily / weekly / monthly reports

## Stage 6: GoalGroup Wizard (High)
- [x] GoalGroup + GoalGroupWizard models (migration 005/006)
- [x] Track taxonomy (6 categories, 40 subcategories, seeded in migration 005)
- [x] Track MCP tools: `list_track_categories`, `list_track_subcategories` (all roles)
- [x] 8-step wizard service: scope → targets → constraints → generate → feasibility → confirm/adjust
- [x] Wizard REST API (`/api/v1/wizards/*`) with ownership guards at every step
- [x] Wizard MCP tools (8 tools, best_pal/admin role)
- [x] OpenClaw: `wizard.tools.ts` and `tracks.tools.ts` bridging REST API
- [x] Feasibility engine: 7 rules (3 blockers + 4 warnings), LLM-enriched explanations
- [x] Draft plan isolation — live plans never mutated before `confirm_goal_group`
- [x] Adjust path ownership validation (target must belong to the wizard's go_getter)
- [x] Wizard TTL: 24 h auto-expiry, bulk-cancel via `expire_stale()`

## Stage 7: Gamification+ (Medium)
- [ ] Extended badge catalogue (subject mastery, consistency champion, etc.)
- [ ] Sibling leaderboard (if multiple go getters)
- [ ] Streak freeze mechanic (bank freeze days via XP)
- [ ] XP shop (redeem XP for streak freezes or bonus praise)

## Stage 8: Frontend (Low)
- [ ] FastAPI Jinja2 HTML dashboard (progress charts, recent activity)
- [ ] React SPA (full-featured web UI, optional)

---

## XP & Streak Formula

```
xp = base_xp × streak_multiplier × mood_bonus

streak_multiplier:
  days 1-2:   1.0
  days 3-6:   1.2
  days 7-13:  1.5
  days 14+:   2.0

mood_bonus:
  1 (terrible): 0.8
  2 (bad):      0.9
  3 (okay):     1.0
  4 (good):     1.1
  5 (great):    1.2
```

## Achievement Badges

| Badge Key        | Name                  | Icon | Trigger                      | XP Bonus |
|------------------|-----------------------|------|------------------------------|----------|
| first_checkin    | First Step!           | 🌟   | First task checked in        | 10       |
| streak_3         | 3-Day Streak!         | 🔥   | 3 consecutive study days     | 15       |
| streak_7         | Week Warrior!         | 🦁   | 7 consecutive study days     | 30       |
| streak_14        | Fortnight Champion!   | 🏆   | 14 consecutive study days    | 75       |
| streak_30        | Monthly Master!       | 👑   | 30 consecutive study days    | 200      |
| xp_50            | 50 XP Club!           | ⭐   | Earn 50 total XP             | 5        |
| xp_100           | Century Scholar!      | 💯   | Earn 100 total XP            | 10       |
| xp_500           | XP Legend!            | 🎖️   | Earn 500 total XP            | 50       |
| weekend_warrior  | Weekend Warrior!      | 🏄   | Check in on both Sat & Sun   | 20       |
