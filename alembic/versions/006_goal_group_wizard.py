"""Add goal_group_wizards table

Revision ID: 006
Revises: 005
Create Date: 2026-02-28 00:00:00.000000

Changes:
  New table:
    goal_group_wizards — multi-turn guided wizard for GoalGroup creation
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "goal_group_wizards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("go_getter_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "collecting_scope",
                "collecting_targets",
                "collecting_constraints",
                "generating_plans",
                "feasibility_check",
                "adjusting",
                "confirmed",
                "cancelled",
                "failed",
            ),
            nullable=False,
            server_default="collecting_scope",
        ),
        sa.Column("group_title", sa.String(200), nullable=True),
        sa.Column("group_description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "target_specs",
            sa.JSON(),
            nullable=True,
            comment="[{target_id, subcategory_id, priority}]",
        ),
        sa.Column(
            "constraints",
            sa.JSON(),
            nullable=True,
            comment="{subcategory_id: {daily_minutes, preferred_days}}",
        ),
        sa.Column(
            "draft_plan_ids",
            sa.JSON(),
            nullable=True,
            comment="[plan_id, ...]",
        ),
        sa.Column("feasibility_passed", sa.SmallInteger(), nullable=True),
        sa.Column(
            "feasibility_risks",
            sa.JSON(),
            nullable=True,
            comment="[{rule_code, level, subcategory_id, detail, llm_explanation, is_blocker}]",
        ),
        sa.Column("goal_group_id", sa.Integer(), nullable=True),
        sa.Column("generation_errors", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["go_getter_id"], ["go_getters.id"]),
        sa.ForeignKeyConstraint(["goal_group_id"], ["goal_groups.id"]),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    op.drop_table("goal_group_wizards")
