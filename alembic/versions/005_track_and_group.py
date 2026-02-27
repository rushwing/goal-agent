"""Add Track taxonomy, GoalGroup, and dynamic re-planning support

Revision ID: 005
Revises: 004
Create Date: 2026-02-28 00:00:00.000000

Changes:
  New tables:
    track_categories       — Study, Fitness, Habit, Mindset, Creative, Life Skills
    track_subcategories    — Math, English, Cardio, etc. (orthogonal via category FK)
    goal_groups            — time-bounded planning windows per GoGetter
    goal_group_changes     — audit log; enforces 1-change-per-7-days constraint

  Altered tables:
    targets   — add subcategory_id (FK, nullable), group_id (FK, nullable)
    plans     — add version, superseded_by_id (self-FK, nullable), group_id (FK, nullable)
    tasks     — add status ENUM(active, cancelled, superseded)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

CATEGORIES = [
    (1, "Study",       "Academic subjects and cognitive skills", "📚", "#4F8EF7"),
    (2, "Fitness",     "Physical health and exercise",           "💪", "#F76F4F"),
    (3, "Habit",       "Daily routines and lifestyle habits",    "🔄", "#4FBF8E"),
    (4, "Mindset",     "Mental wellness and self-reflection",    "🧠", "#A06FF7"),
    (5, "Creative",    "Arts, music, and creative expression",   "🎨", "#F7C94F"),
    (6, "Life Skills", "Practical real-world competencies",      "🛠️", "#6FA8F7"),
]

SUBCATEGORIES = [
    # Study
    (1,  1, "Math",            1),
    (2,  1, "Chinese",         2),
    (3,  1, "English",         3),
    (4,  1, "Science",         4),
    (5,  1, "History",         5),
    (6,  1, "Programming",     6),
    (7,  1, "Reading",         7),
    (8,  1, "Other",           99),
    # Fitness
    (9,  2, "Cardio",          1),
    (10, 2, "Strength",        2),
    (11, 2, "Flexibility",     3),
    (12, 2, "Swimming",        4),
    (13, 2, "Sports",          5),
    (14, 2, "Other",           99),
    # Habit
    (15, 3, "Sleep",           1),
    (16, 3, "Diet",            2),
    (17, 3, "Hydration",       3),
    (18, 3, "Screen Time",     4),
    (19, 3, "Morning Routine", 5),
    (20, 3, "Other",           99),
    # Mindset
    (21, 4, "Journaling",      1),
    (22, 4, "Meditation",      2),
    (23, 4, "Gratitude",       3),
    (24, 4, "Other",           99),
    # Creative
    (25, 5, "Drawing",         1),
    (26, 5, "Music",           2),
    (27, 5, "Creative Writing",3),
    (28, 5, "Photography",     4),
    (29, 5, "Other",           99),
    # Life Skills
    (30, 6, "Finance",         1),
    (31, 6, "Cooking",         2),
    (32, 6, "Social Skills",   3),
    (33, 6, "Other",           99),
]


def upgrade() -> None:
    # ── track_categories ───────────────────────────────────────────────────
    op.create_table(
        "track_categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", name="uq_track_category_name"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # ── track_subcategories ────────────────────────────────────────────────
    op.create_table(
        "track_subcategories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["track_categories.id"]),
        sa.UniqueConstraint("category_id", "name", name="uq_track_subcategory_cat_name"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # ── goal_groups ────────────────────────────────────────────────────────
    op.create_table(
        "goal_groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("go_getter_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "completed", "archived"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("last_change_at", sa.DateTime(), nullable=True),
        sa.Column(
            "replan_status",
            sa.Enum("idle", "in_progress", "failed"),
            nullable=False,
            server_default="idle",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["go_getter_id"], ["go_getters.id"]),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # ── goal_group_changes ─────────────────────────────────────────────────
    op.create_table(
        "goal_group_changes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column(
            "change_type",
            sa.Enum(
                "target_added",
                "target_removed",
                "target_paused",
                "priority_changed",
                "end_date_extended",
            ),
            nullable=False,
        ),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("triggered_replan_at", sa.DateTime(), nullable=True),
        sa.Column("replan_plan_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["goal_groups.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"]),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # ── alter targets ──────────────────────────────────────────────────────
    op.add_column("targets", sa.Column("subcategory_id", sa.Integer(), nullable=True))
    op.add_column("targets", sa.Column("group_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_targets_subcategory", "targets", "track_subcategories", ["subcategory_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_targets_group", "targets", "goal_groups", ["group_id"], ["id"]
    )

    # ── alter plans ────────────────────────────────────────────────────────
    op.add_column("plans", sa.Column("version", sa.SmallInteger(), nullable=False, server_default="1"))
    op.add_column("plans", sa.Column("superseded_by_id", sa.Integer(), nullable=True))
    op.add_column("plans", sa.Column("group_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_plans_superseded_by", "plans", "plans", ["superseded_by_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_plans_group", "plans", "goal_groups", ["group_id"], ["id"]
    )

    # ── alter tasks ────────────────────────────────────────────────────────
    op.add_column(
        "tasks",
        sa.Column(
            "status",
            sa.Enum("active", "cancelled", "superseded"),
            nullable=False,
            server_default="active",
        ),
    )

    # ── seed track_categories ──────────────────────────────────────────────
    track_categories = sa.table(
        "track_categories",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("icon", sa.String),
        sa.column("color", sa.String),
        sa.column("sort_order", sa.SmallInteger),
    )
    op.bulk_insert(
        track_categories,
        [
            {"id": c[0], "name": c[1], "description": c[2], "icon": c[3], "color": c[4], "sort_order": i}
            for i, c in enumerate(CATEGORIES, start=1)
        ],
    )

    # ── seed track_subcategories ───────────────────────────────────────────
    track_subcategories = sa.table(
        "track_subcategories",
        sa.column("id", sa.Integer),
        sa.column("category_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("sort_order", sa.SmallInteger),
    )
    op.bulk_insert(
        track_subcategories,
        [
            {"id": s[0], "category_id": s[1], "name": s[2], "sort_order": s[3]}
            for s in SUBCATEGORIES
        ],
    )


def downgrade() -> None:
    # tasks
    op.drop_column("tasks", "status")

    # plans
    op.drop_constraint("fk_plans_group", "plans", type_="foreignkey")
    op.drop_constraint("fk_plans_superseded_by", "plans", type_="foreignkey")
    op.drop_column("plans", "group_id")
    op.drop_column("plans", "superseded_by_id")
    op.drop_column("plans", "version")

    # targets
    op.drop_constraint("fk_targets_group", "targets", type_="foreignkey")
    op.drop_constraint("fk_targets_subcategory", "targets", type_="foreignkey")
    op.drop_column("targets", "group_id")
    op.drop_column("targets", "subcategory_id")

    # new tables (order matters for FK)
    op.drop_table("goal_group_changes")
    op.drop_table("goal_groups")
    op.drop_table("track_subcategories")
    op.drop_table("track_categories")
