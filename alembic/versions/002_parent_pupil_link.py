"""Add parent_id FK to pupils (issue #2: parent-pupil ownership)

Revision ID: 002
Revises: 001
Create Date: 2026-02-24 00:00:00.000000

Bootstrap note: existing pupils will have parent_id=NULL. Admins should assign
parent_id values via the admin API or directly in the DB before enforcing
ownership in a multi-family deployment.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pupils",
        sa.Column("parent_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_pupils_parent_id",
        "pupils",
        "parents",
        ["parent_id"],
        ["id"],
    )
    op.create_index("ix_pupils_parent_id", "pupils", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_pupils_parent_id", table_name="pupils")
    op.drop_constraint("fk_pupils_parent_id", "pupils", type_="foreignkey")
    op.drop_column("pupils", "parent_id")
