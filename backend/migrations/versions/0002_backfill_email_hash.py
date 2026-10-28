"""Backfill users.email_hash using EMAIL_HASH_SECRET.

Revision ID: 0002_backfill_email_hash
Revises: 0001_initial_schema
Create Date: 2026-10-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.core.security import create_email_hash

revision: str = "0002_backfill_email_hash"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    users_table = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("email", sa.String),
        sa.column("email_hash", sa.String),
    )

    rows = connection.execute(
        sa.select(users_table.c.id, users_table.c.email).where(
            users_table.c.email.is_not(None)
        )
    ).fetchall()

    for user_id, email in rows:
        if email:
            new_hash = create_email_hash(email)
            connection.execute(
                users_table.update()
                .where(users_table.c.id == user_id)
                .values(email_hash=new_hash)
            )


def downgrade() -> None:
    # Hash backfill is non-destructive and preserves existing login capability
    pass
