"""Add reference_materials and search_errors to goal_group_wizards

Revision ID: 007
Revises: 006
Create Date: 2026-03-02 00:00:00.000000

Changes:
  goal_group_wizards:
    + reference_materials  JSON nullable  -- {str(target_id): [{title,source,url,key_points}]}
    + search_errors        JSON nullable  -- {str(target_id): error_message}
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "goal_group_wizards",
        sa.Column(
            "reference_materials",
            sa.JSON(),
            nullable=True,
            comment="{str(target_id): [{title,source,url,key_points}]}",
        ),
    )
    op.add_column(
        "goal_group_wizards",
        sa.Column(
            "search_errors",
            sa.JSON(),
            nullable=True,
            comment="{str(target_id): error_message}",
        ),
    )


def downgrade() -> None:
    op.drop_column("goal_group_wizards", "search_errors")
    op.drop_column("goal_group_wizards", "reference_materials")
