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
1. One active Plan per Target
2. One active Target per (go_getter_id, subcategory_id) — same-track uniqueness
3. One active GoalGroup per GoGetter at a time
4. GoalGroup changes: max 1 per rolling 7 days (check `last_change_at`)
5. Re-planning: current ISO week stays frozen; regenerate from next Monday
6. Re-planning is atomic: new Plan created as `draft` → validate → swap to `active`, old → `superseded`
7. Concurrent re-plan guard: optimistic lock via `goal_groups.replan_status` (idle → in_progress)

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
    target.py            # Target, TargetStatus, VacationType
    plan.py              # Plan, PlanStatus
    task.py              # Task, TaskStatus (add: active|cancelled|superseded)
    weekly_milestone.py  # WeeklyMilestone
    check_in.py          # CheckIn
    # TODO (migration 005):
    track_category.py    # TrackCategory
    track_subcategory.py # TrackSubcategory
    goal_group.py        # GoalGroup, GoalGroupChange
  api/v1/
    plans.py             # Target + Plan endpoints
    checkins.py          # CheckIn endpoints
    reports.py           # Report endpoints
    admin.py             # Admin endpoints
  services/
    plan_generator.py    # LLM plan generation
    github_service.py    # GitHub commit
  crud/                  # One file per model
alembic/versions/
  001_initial_schema.py
  002_parent_pupil_link.py
  003_report_unique_constraint.py
  004_rename_to_go_getter_best_pal.py
  # Next: 005_track_and_group.py
scripts/
  deploy.sh              # Full deploy (uv sync + migrate + systemd)
  provision.sh           # First-time MariaDB setup (to be created)
  backup.sh              # Daily DB backup
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
