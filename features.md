# Vacation Study Planner – Feature Stages

## Stage 1: Foundation (Critical)
- [x] Project setup (pyproject.toml, .env.example)
- [x] SQLAlchemy 2.0 async models (all 10 tables)
- [x] Alembic async migrations
- [x] Generic CRUD base + individual CRUD modules
- [x] FastMCP server with role-based auth (X-Telegram-Chat-Id)
- [x] Admin MCP tools: add/update/remove/list pupils & parents
- [x] FastAPI main app + FastMCP mount (single process)

## Stage 2: Planning Engine (Critical)
- [x] Target CRUD (create_target, update_target, delete_target, list_targets)
- [x] Kimi AI plan generation (generate_plan → structured JSON)
- [x] Milestone + task DB persistence
- [x] GitHub auto-commit of generated plans (Markdown)
- [x] Plan MCP tools: create_target, generate_plan, update_plan, list_plans, get_plan_detail

## Stage 3: Check-in System (Critical)
- [x] Task check-in: mood score, duration, notes
- [x] Streak service: XP formula, streak_multiplier, mood_bonus
- [x] Achievement unlocking (first_checkin, streak_3/7/14/30, xp milestones)
- [x] Praise engine: LLM + 20+ offline fallback templates
- [x] Check-in MCP tools: list_today_tasks, list_week_tasks, checkin_task, skip_task, get_pupil_progress

## Stage 4: Reports (High)
- [x] Daily report (Markdown, GitHub commit)
- [x] Weekly report (Markdown, GitHub commit)
- [x] Monthly report (Markdown, GitHub commit)
- [x] Report MCP tools: generate_daily/weekly/monthly_report, list_reports

## Stage 5: Telegram & OpenClaw Integration (High)
- [x] Telegram service (httpx async, parent + pupil bots)
- [x] APScheduler cron jobs (morning tasks, evening reminders, weekly/monthly reports)
- [x] OpenClaw TypeScript plugin (axios HTTP client, X-Telegram-Chat-Id injection)
- [x] Group notifications for reports

## Stage 6: Gamification+ (Medium)
- [ ] Extended badge catalogue (subject mastery, consistency champion, etc.)
- [ ] Sibling leaderboard (if multiple pupils)
- [ ] Streak freeze mechanic (bank freeze days via XP)
- [ ] XP shop (redeem XP for streak freezes or bonus praise)

## Stage 7: Frontend (Low)
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
