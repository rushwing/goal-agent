"""Rename pupil/parent terminology to go_getter/best_pal

Revision ID: 004
Revises: 003
Create Date: 2026-02-25 00:00:00.000000

Renames:
  Tables:    parents  → best_pals,  pupils  → go_getters
  Columns:   pupils.parent_id  → go_getters.best_pal_id
             targets.pupil_id  → targets.go_getter_id
             check_ins.pupil_id  → check_ins.go_getter_id
             reports.pupil_id  → reports.go_getter_id
             achievements.pupil_id  → achievements.go_getter_id
  Enum vals: notifications.recipient_type:  pupil→go_getter, parent→best_pal
  Constraints: uq_checkin_task_pupil → uq_checkin_task_go_getter
               uq_achievement_pupil_badge → uq_achievement_go_getter_badge
               uq_report_identity columns updated
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_fk_name(conn, table: str, column: str, ref_table: str) -> str | None:
    """Find the auto-generated FK constraint name in MySQL/MariaDB."""
    result = conn.execute(
        sa.text(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table
              AND COLUMN_NAME = :column
              AND REFERENCED_TABLE_NAME = :ref_table
            LIMIT 1
            """
        ),
        {"table": table, "column": column, "ref_table": ref_table},
    )
    row = result.fetchone()
    return row[0] if row else None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Drop FKs that reference tables/columns we're about to rename
    # ------------------------------------------------------------------

    for table, column, ref_table in [
        ("check_ins", "pupil_id", "pupils"),
        ("reports", "pupil_id", "pupils"),
        ("achievements", "pupil_id", "pupils"),
        ("targets", "pupil_id", "pupils"),
    ]:
        fk = _get_fk_name(conn, table, column, ref_table)
        if fk:
            op.drop_constraint(fk, table, type_="foreignkey")

    # FK from pupils.parent_id → parents.id (named explicitly in migration 002)
    # Drop FK before index — MariaDB requires this order
    op.drop_constraint("fk_pupils_parent_id", "pupils", type_="foreignkey")
    op.drop_index("ix_pupils_parent_id", table_name="pupils")

    # ------------------------------------------------------------------
    # 2. Drop old unique constraints (will be recreated with new names)
    # ------------------------------------------------------------------

    op.drop_constraint("uq_checkin_task_pupil", "check_ins", type_="unique")
    op.drop_constraint("uq_achievement_pupil_badge", "achievements", type_="unique")
    op.drop_constraint("uq_report_identity", "reports", type_="unique")

    # ------------------------------------------------------------------
    # 3. Rename tables
    # ------------------------------------------------------------------

    op.rename_table("parents", "best_pals")
    op.rename_table("pupils", "go_getters")

    # ------------------------------------------------------------------
    # 4. Rename columns
    # ------------------------------------------------------------------

    op.alter_column(
        "go_getters",
        "parent_id",
        new_column_name="best_pal_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "targets",
        "pupil_id",
        new_column_name="go_getter_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "check_ins",
        "pupil_id",
        new_column_name="go_getter_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "reports",
        "pupil_id",
        new_column_name="go_getter_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "achievements",
        "pupil_id",
        new_column_name="go_getter_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # 5. Update notifications enum values
    # ------------------------------------------------------------------

    # Step 1: widen enum to accept both old and new values
    op.alter_column(
        "notifications",
        "recipient_type",
        existing_type=sa.Enum("pupil", "parent", "group"),
        type_=sa.Enum("pupil", "parent", "group", "go_getter", "best_pal"),
        nullable=False,
    )
    # Step 2: migrate data
    op.execute(
        "UPDATE notifications SET recipient_type = 'go_getter' WHERE recipient_type = 'pupil'"
    )
    op.execute(
        "UPDATE notifications SET recipient_type = 'best_pal' WHERE recipient_type = 'parent'"
    )
    # Step 3: narrow enum to new values only
    op.alter_column(
        "notifications",
        "recipient_type",
        existing_type=sa.Enum("pupil", "parent", "group", "go_getter", "best_pal"),
        type_=sa.Enum("go_getter", "best_pal", "group"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # 6. Recreate unique constraints with new names
    # ------------------------------------------------------------------

    op.create_unique_constraint(
        "uq_checkin_task_go_getter", "check_ins", ["task_id", "go_getter_id"]
    )
    op.create_unique_constraint(
        "uq_achievement_go_getter_badge", "achievements", ["go_getter_id", "badge_key"]
    )
    op.create_unique_constraint(
        "uq_report_identity", "reports", ["go_getter_id", "report_type", "period_start"]
    )

    # ------------------------------------------------------------------
    # 7. Recreate FKs with new names pointing to renamed tables
    # ------------------------------------------------------------------

    op.create_foreign_key(
        "fk_targets_go_getter_id",
        "targets",
        "go_getters",
        ["go_getter_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_check_ins_go_getter_id",
        "check_ins",
        "go_getters",
        ["go_getter_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_reports_go_getter_id",
        "reports",
        "go_getters",
        ["go_getter_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_achievements_go_getter_id",
        "achievements",
        "go_getters",
        ["go_getter_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_go_getters_best_pal_id",
        "go_getters",
        "best_pals",
        ["best_pal_id"],
        ["id"],
    )
    op.create_index("ix_go_getters_best_pal_id", "go_getters", ["best_pal_id"])


def downgrade() -> None:
    # Drop recreated FKs
    op.drop_index("ix_go_getters_best_pal_id", table_name="go_getters")
    op.drop_constraint("fk_go_getters_best_pal_id", "go_getters", type_="foreignkey")
    op.drop_constraint("fk_achievements_go_getter_id", "achievements", type_="foreignkey")
    op.drop_constraint("fk_reports_go_getter_id", "reports", type_="foreignkey")
    op.drop_constraint("fk_check_ins_go_getter_id", "check_ins", type_="foreignkey")
    op.drop_constraint("fk_targets_go_getter_id", "targets", type_="foreignkey")

    # Drop new unique constraints
    op.drop_constraint("uq_report_identity", "reports", type_="unique")
    op.drop_constraint("uq_achievement_go_getter_badge", "achievements", type_="unique")
    op.drop_constraint("uq_checkin_task_go_getter", "check_ins", type_="unique")

    # Revert enum
    op.alter_column(
        "notifications",
        "recipient_type",
        existing_type=sa.Enum("go_getter", "best_pal", "group"),
        type_=sa.Enum("pupil", "parent", "group", "go_getter", "best_pal"),
        nullable=False,
    )
    op.execute(
        "UPDATE notifications SET recipient_type = 'pupil' WHERE recipient_type = 'go_getter'"
    )
    op.execute(
        "UPDATE notifications SET recipient_type = 'parent' WHERE recipient_type = 'best_pal'"
    )
    op.alter_column(
        "notifications",
        "recipient_type",
        existing_type=sa.Enum("pupil", "parent", "group", "go_getter", "best_pal"),
        type_=sa.Enum("pupil", "parent", "group"),
        nullable=False,
    )

    # Rename columns back
    op.alter_column(
        "achievements",
        "go_getter_id",
        new_column_name="pupil_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "reports",
        "go_getter_id",
        new_column_name="pupil_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "check_ins",
        "go_getter_id",
        new_column_name="pupil_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "targets",
        "go_getter_id",
        new_column_name="pupil_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "go_getters",
        "best_pal_id",
        new_column_name="parent_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # Rename tables back
    op.rename_table("go_getters", "pupils")
    op.rename_table("best_pals", "parents")

    # Restore old unique constraints
    op.create_unique_constraint(
        "uq_report_identity", "reports", ["pupil_id", "report_type", "period_start"]
    )
    op.create_unique_constraint(
        "uq_achievement_pupil_badge", "achievements", ["pupil_id", "badge_key"]
    )
    op.create_unique_constraint("uq_checkin_task_pupil", "check_ins", ["task_id", "pupil_id"])

    # Restore FKs
    op.create_foreign_key("fk_pupils_parent_id", "pupils", "parents", ["parent_id"], ["id"])
    op.create_index("ix_pupils_parent_id", "pupils", ["parent_id"])
