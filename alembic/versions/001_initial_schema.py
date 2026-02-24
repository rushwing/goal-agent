"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Parents table
    op.create_table(
        "parents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_chat_id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # Pupils table
    op.create_table(
        "pupils",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("grade", sa.String(20), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("xp_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_longest", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_last_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_chat_id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # Targets table
    op.create_table(
        "targets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pupil_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "vacation_type",
            sa.Enum("summer", "winter", "spring", "autumn", "other"),
            nullable=False,
        ),
        sa.Column("vacation_year", sa.SmallInteger(), nullable=False),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="3"),
        sa.Column(
            "status",
            sa.Enum("active", "completed", "cancelled"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pupil_id"], ["pupils.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # Plans table
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("total_weeks", sa.SmallInteger(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "active", "completed", "cancelled"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("github_commit_sha", sa.String(40), nullable=True),
        sa.Column("github_file_path", sa.String(500), nullable=True),
        sa.Column("llm_prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # Weekly milestones table
    op.create_table(
        "weekly_milestones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("week_number", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("total_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # Tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("milestone_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("sequence_in_day", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("estimated_minutes", sa.SmallInteger(), nullable=False, server_default="30"),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="10"),
        sa.Column(
            "task_type",
            sa.Enum("reading", "writing", "math", "practice", "review", "project", "quiz", "other"),
            nullable=False,
            server_default="practice",
        ),
        sa.Column("is_optional", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["milestone_id"], ["weekly_milestones.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # Check-ins table
    op.create_table(
        "check_ins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("pupil_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("completed", "skipped"),
            nullable=False,
            server_default="completed",
        ),
        sa.Column("mood_score", sa.SmallInteger(), nullable=True),
        sa.Column("duration_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("xp_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_at_checkin", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("praise_message", sa.Text(), nullable=True),
        sa.Column("skip_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pupil_id"], ["pupils.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "pupil_id", name="uq_checkin_task_pupil"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # Reports table
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pupil_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.Enum("daily", "weekly", "monthly"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("content_md", sa.Text(16777215), nullable=False),  # MEDIUMTEXT
        sa.Column("tasks_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tasks_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tasks_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xp_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("github_commit_sha", sa.String(40), nullable=True),
        sa.Column("github_file_path", sa.String(500), nullable=True),
        sa.Column("sent_to_telegram", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pupil_id"], ["pupils.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # Achievements table
    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pupil_id", sa.Integer(), nullable=False),
        sa.Column("badge_key", sa.String(50), nullable=False),
        sa.Column("badge_name", sa.String(100), nullable=False),
        sa.Column("badge_icon", sa.String(10), nullable=False),
        sa.Column("xp_bonus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pupil_id"], ["pupils.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pupil_id", "badge_key", name="uq_achievement_pupil_badge"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # Notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipient_type", sa.Enum("pupil", "parent", "group"), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=True),
        sa.Column(
            "channel",
            sa.Enum("telegram_dm", "telegram_group"),
            nullable=False,
        ),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column(
            "notification_type",
            sa.Enum(
                "daily_tasks",
                "evening_reminder",
                "weekly_report",
                "monthly_report",
                "achievement",
                "praise",
                "generic",
            ),
            nullable=False,
            server_default="generic",
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "sent", "failed"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("achievements")
    op.drop_table("reports")
    op.drop_table("check_ins")
    op.drop_table("tasks")
    op.drop_table("weekly_milestones")
    op.drop_table("plans")
    op.drop_table("targets")
    op.drop_table("pupils")
    op.drop_table("parents")
