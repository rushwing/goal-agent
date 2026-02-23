"""Add unique constraint on reports(pupil_id, report_type, period_start) (issue #5: idempotency)

Revision ID: 003
Revises: 002
Create Date: 2026-02-24 00:00:00.000000

Note: if duplicate reports already exist in the DB, remove them before running
this migration (keep the row with the lowest id per group).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_report_identity",
        "reports",
        ["pupil_id", "report_type", "period_start"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_report_identity", "reports", type_="unique")
