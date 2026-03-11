"""add experiment_id to streams

Revision ID: 87d93def2ccd
Revises: 6986444486d4
Create Date: 2026-03-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "87d93def2ccd"
down_revision: str | Sequence[str] | None = "6986444486d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "streams",
        sa.Column("experiment_id", sa.String(50), nullable=True),
    )
    op.create_index(
        "ix_streams_experiment",
        "streams",
        ["user_id", "experiment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_streams_experiment", table_name="streams")
    op.drop_column("streams", "experiment_id")
