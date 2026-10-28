"""Track who initiated each pending friendship.

Revision ID: 0003_friendship_requester
Revises: 0002_backfill_email_hash
Create Date: 2026-10-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_friendship_requester"
down_revision: Union[str, None] = "0002_backfill_email_hash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "friendships",
        sa.Column("requested_by", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_friendships_requested_by_users",
        "friendships",
        "users",
        ["requested_by"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_friendships_requested_by_users", "friendships", type_="foreignkey"
    )
    op.drop_column("friendships", "requested_by")