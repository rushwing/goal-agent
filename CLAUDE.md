# goal-agent — Project Guide for Claude Agents

## Stack
- **Runtime**: Python 3.12, FastAPI (async), SQLAlchemy 2 (async), Alembic
- **DB**: MariaDB (utf8mb4_unicode_ci). No partial unique indexes — enforce uniqueness at service layer.
- **Package manager**: uv (`uv run`, `uv sync --no-dev`)
- **Deploy target**: Raspberry Pi via systemd + `scripts/deploy.sh`
- **LLM**: Claude API (claude-sonnet-4-6 default)

## Key Conventions
- All models inherit `Base, TimestampMixin` from `app/models/base.py`
- Async sessions everywhere: `AsyncSession`, `await db.execute(...)`, `await db.flush()`
- Never use `db.commit()` in routes — handled by middleware
- CRUD lives in `app/crud/`, service logic in `app/services/`
- Enums: define Python `enum.Enum` in the model file, mirror as `sa.Enum(...)` in migration
- Never physical-delete records that have check-ins or audit history; use status fields

## Architecture: Data Hierarchy
```
GoGetter
  └── GoalGroup (time-bounded planning window, optional)
        └── Target (goal, has subcategory_id → TrackSubcategory)
              └── Plan (versioned; old plans get status=superseded)
                    └── WeeklyMilestone
                          └── Task (status: active | cancelled | superseded)
                                └── CheckIn
```

## Core Constraints (enforce at service layer)
1. One active Plan per Target — enforced in `plan_generator.generate_plan()`
2. One active Target per `(go_getter_id, subcategory_id)` — enforced in `POST /targets`, `PATCH /targets`, and `add_target_to_group()` via `assert_subcategory_available()`
3. One active GoalGroup per GoGetter at a time — enforced in `POST /goal-groups` via `get_active_for_go_getter()` and in `wizard_service.confirm()`
4. GoalGroup changes: max 1 per rolling 7 days — enforced in `assert_change_allowed()` (checks `goal_groups.last_change_at`)
5. Re-planning: current ISO week stays frozen; regenerate from next Monday (`_next_monday()`)
6. Re-planning is atomic: new Plan created as `draft` → validate → swap to `active`, old → `cancelled` + `superseded_by_id` set
7. Concurrent re-plan guard: optimistic lock via `goal_groups.replan_status` (CAS `idle → in_progress`, see `acquire_replan_lock()`)
8. Tasks are never physically deleted — use `status=superseded` to preserve check-in history
9. One active Wizard per GoGetter at a time — enforced in `wizard_service.create_wizard()`; wizards expire after 24 h (`expires_at`)
10. Wizard draft plans never deactivate live plans — deactivation happens only at `wizard_service.confirm()` time

## Track Taxonomy (seeded in migration 005)
| Category   | Subcategories |
|------------|---------------|
| Study      | Math, Chinese, English, Science, History, Programming, Reading, Other |
| Fitness    | Cardio, Strength, Flexibility, Swimming, Sports, Other |
| Habit      | Sleep, Diet, Hydration, Screen Time, Morning Routine, Other |
| Mindset    | Journaling, Meditation, Gratitude, Other |
| Creative   | Drawing, Music, Creative Writing, Photography, Other |
| Life Skills| Finance, Cooking, Social Skills, Other |

## File Map
```
app/
  models/
    base.py              # Base, TimestampMixin
    go_getter.py         # GoGetter
    track_category.py    # TrackCategory
    track_subcategory.py # TrackSubcategory
    goal_group.py        # GoalGroup, GoalGroupChange, GoalGroupStatus, ReplanStatus, ChangeType
    goal_group_wizard.py # GoalGroupWizard, WizardStatus, TERMINAL_STATUSES
    target.py            # Target, TargetStatus, VacationType
    plan.py              # Plan, PlanStatus (+ version, superseded_by_id, group_id)
    task.py              # Task, TaskType, TaskStatus (active|cancelled|superseded)
    weekly_milestone.py  # WeeklyMilestone
    check_in.py          # CheckIn
  api/v1/
    plans.py             # Target + Plan endpoints (subcategory uniqueness enforced here)
    goal_groups.py       # GoalGroup CRUD + add/remove target endpoints
    wizards.py           # Wizard multi-step creation endpoints (POST /, scope, targets, constraints, confirm, ...)
    tracks.py            # GET /tracks/categories, GET /tracks/subcategories
    checkins.py          # CheckIn endpoints
    reports.py           # Report endpoints
    admin.py             # Admin endpoints
  schemas/
    wizard.py            # WizardCreate, ScopeRequest, TargetsRequest, ConstraintsRequest, AdjustRequest, WizardResponse
  services/
    plan_generator.py    # LLM plan generation (initial_status, deactivate_existing, optional daily_study_minutes)
    goal_group_service.py # Constraint checks + atomic re-planning orchestration
    wizard_service.py    # Wizard orchestration: create → scope → targets → constraints → confirm
    feasibility_service.py # 7-rule feasibility engine + LLM enrichment (FeasibilityRisk dataclass)
    github_service.py    # GitHub commit
  crud/
    goal_groups.py       # GoalGroup CRUD + acquire/release_replan_lock
    wizards.py           # create, get, get_active_for_go_getter, update_wizard, expire_stale
    tracks.py            # Track category/subcategory reads
    targets.py / plans.py / tasks.py / ...
alembic/versions/
  001_initial_schema.py
  002_parent_pupil_link.py
  003_report_unique_constraint.py
  004_rename_to_go_getter_best_pal.py
  005_track_and_group.py  # Track taxonomy, GoalGroup, task status, plan versioning
  006_goal_group_wizard.py # goal_group_wizards table; WizardStatus enum; expires_at TTL
scripts/
  setup.sh               # Bootstrap project: install uv, sync deps, copy .env.example
  db_init.sh             # First-time MariaDB DB + user creation, then migrate (run once)
  migrate.sh             # Run Alembic migrations (wraps `uv run alembic`)
  dev.sh                 # Start API server with hot-reload (development)
  test.sh                # Run test suite (in-memory SQLite, no MariaDB needed)
  lint.sh                # Run ruff check + format
  deploy.sh              # Full deploy: uv sync + migrate + systemd reload + cron
  backup.sh              # Dump MariaDB + .env to backups/; auto-prune after 7 days
```

## First-time Setup

```bash
# 1. Bootstrap Python env and copy .env.example → .env
./scripts/setup.sh --dev          # add --dev for test/lint deps

# 2. Fill in secrets
$EDITOR .env                      # set DATABASE_URL, DB_*, tokens, keys

# 3. Create MariaDB database + user, then run migrations
./scripts/db_init.sh              # root with socket auth (no password prompt)
./scripts/db_init.sh -p <pw>      # or pass MariaDB root password explicitly

# 4. Start the development server
./scripts/dev.sh
```

`db_init.sh` reads app credentials from `.env` — either the individual `DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD` vars or by parsing `DATABASE_URL`. Supports `--skip-migrate` to skip the Alembic step. Idempotent: safe to re-run.

## Wizard Feature (migration 006)

Multi-turn guided GoalGroup creation flow at `POST /api/v1/wizards`.

### State Machine
```
collecting_scope
  └─► collecting_targets
        └─► collecting_constraints
              └─► generating_plans   ← (re-entry from adjusting)
                    └─► feasibility_check
                          ├─► confirmed   (creates GoalGroup + activates draft plans)
                          └─► adjusting ──► generating_plans
(any) ──► cancelled / failed
```
Terminal states: `confirmed`, `cancelled`, `failed`.

### Wizard API Endpoints
| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/wizards/` | Create; 409 if active wizard exists |
| GET | `/api/v1/wizards/{id}` | Resume / status check |
| POST | `/api/v1/wizards/{id}/scope` | Set time window (≥ 7 days) |
| POST | `/api/v1/wizards/{id}/targets` | Set target list; subcategory_id normalised from DB |
| POST | `/api/v1/wizards/{id}/constraints` | Set per-target constraints; triggers plan gen + feasibility |
| GET | `/api/v1/wizards/{id}/feasibility` | Return risks + passed flag |
| POST | `/api/v1/wizards/{id}/adjust` | Partial patch; re-generates + re-checks |
| POST | `/api/v1/wizards/{id}/confirm` | Creates GoalGroup + activates plans; 409 on blockers |
| DELETE | `/api/v1/wizards/{id}` | Cancel wizard + draft plans |

### Feasibility Rules
| Rule code | Level | Condition |
|-----------|-------|-----------|
| `RULE_SPAN_TOO_SHORT` | error (blocker) | date range < 7 days |
| `RULE_DUPLICATE_SUBCATEGORY` | error (blocker) | same subcategory_id twice in target_specs |
| `RULE_EXISTING_ACTIVE_SUBCATEGORY` | error (blocker) | subcategory already has an active Plan for go_getter |
| `RULE_EXISTING_ACTIVE_GROUP` | warning | go_getter already has an active GoalGroup |
| `RULE_OVERLOAD` | warning | total daily_minutes > grade-based limit (120 min) |
| `RULE_SINGLE_TARGET_OVERLOAD` | warning | any single target daily_minutes > 120 |
| `RULE_TOO_FEW_DAYS` | warning | any target preferred_days has < 3 entries |

`feasibility_passed = 1` when no blocker (error-level) risks exist. `confirm()` is blocked when `feasibility_passed == 0` or `generation_errors` is non-empty.

### Key Implementation Notes
- Constraints JSON stored with **string keys** (`str(subcategory_id)`) due to JSON serialisation; look up with `wizard.constraints.get(str(subcategory_id))`.
- `plan_generator.generate_plan(..., deactivate_existing=False)` is used during draft generation to preserve live plans; deactivation happens only at `confirm()`.
- `expire_stale(db)` bulk-cancels wizards past `expires_at`; run periodically (cron / startup).

## Running Tests
```bash
uv sync --extra dev
uv run python -m pytest
# or
./scripts/test.sh
```

## Agent Team Tips
- Teammates should own **separate files** — avoid editing the same file concurrently
- Schema changes (migration + model) should always be done by one teammate
- Service logic can be parallelised once models are stable
- Use the shared task list to self-assign work
