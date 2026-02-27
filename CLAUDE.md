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
3. One active GoalGroup per GoGetter at a time — enforced in `POST /goal-groups` via `get_active_for_go_getter()`
4. GoalGroup changes: max 1 per rolling 7 days — enforced in `assert_change_allowed()` (checks `goal_groups.last_change_at`)
5. Re-planning: current ISO week stays frozen; regenerate from next Monday (`_next_monday()`)
6. Re-planning is atomic: new Plan created as `draft` → validate → swap to `active`, old → `cancelled` + `superseded_by_id` set
7. Concurrent re-plan guard: optimistic lock via `goal_groups.replan_status` (CAS `idle → in_progress`, see `acquire_replan_lock()`)
8. Tasks are never physically deleted — use `status=superseded` to preserve check-in history

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
    target.py            # Target, TargetStatus, VacationType
    plan.py              # Plan, PlanStatus (+ version, superseded_by_id, group_id)
    task.py              # Task, TaskType, TaskStatus (active|cancelled|superseded)
    weekly_milestone.py  # WeeklyMilestone
    check_in.py          # CheckIn
  api/v1/
    plans.py             # Target + Plan endpoints (subcategory uniqueness enforced here)
    goal_groups.py       # GoalGroup CRUD + add/remove target endpoints
    tracks.py            # GET /tracks/categories, GET /tracks/subcategories
    checkins.py          # CheckIn endpoints
    reports.py           # Report endpoints
    admin.py             # Admin endpoints
  services/
    plan_generator.py    # LLM plan generation (initial_status, optional daily_study_minutes)
    goal_group_service.py # Constraint checks + atomic re-planning orchestration
    github_service.py    # GitHub commit
  crud/
    goal_groups.py       # GoalGroup CRUD + acquire/release_replan_lock
    tracks.py            # Track category/subcategory reads
    targets.py / plans.py / tasks.py / ...
alembic/versions/
  001_initial_schema.py
  002_parent_pupil_link.py
  003_report_unique_constraint.py
  004_rename_to_go_getter_best_pal.py
  005_track_and_group.py  # Track taxonomy, GoalGroup, task status, plan versioning
scripts/
  deploy.sh              # Full deploy (uv sync + migrate + systemd + cron)
  provision.sh           # First-time MariaDB setup (run once as root)
  backup.sh              # Daily DB backup (cron installed by deploy.sh)
```

## Running Tests
```bash
uv sync --extra dev
uv run pytest
# or
./scripts/test.sh
```

## Agent Team Tips
- Teammates should own **separate files** — avoid editing the same file concurrently
- Schema changes (migration + model) should always be done by one teammate
- Service logic can be parallelised once models are stable
- Use the shared task list to self-assign work
