"""Expand faculty_code column length to 100 characters.

Revision ID: 0004_expand_faculty_code
Revises: 0003_friendship_requester
Create Date: 2026-10-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_expand_faculty_code"
down_revision: Union[str, None] = "0003_friendship_requester"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.alter_column(
        "profiles",
        "faculty_code",
        existing_type=sa.String(length=20),
        type_=sa.String(length=100),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "profiles",
        "faculty_code",
        existing_type=sa.String(length=100),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
