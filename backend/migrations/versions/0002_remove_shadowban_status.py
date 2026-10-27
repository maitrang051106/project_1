"""Remove the shadowban user status."""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0002_remove_shadowban_status"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET status = CASE WHEN trust_score <= 0 THEN 'banned' ELSE 'active' END
        WHERE status = 'shadowban' OR (trust_score <= 0 AND status <> 'banned')
        """
    )
    op.alter_column(
        "users",
        "status",
        existing_type=mysql.ENUM("active", "shadowban", "banned", name="user_status"),
        type_=mysql.ENUM("active", "banned", name="user_status"),
        existing_nullable=False,
        existing_server_default="active",
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "status",
        existing_type=mysql.ENUM("active", "banned", name="user_status"),
        type_=mysql.ENUM("active", "shadowban", "banned", name="user_status"),
        existing_nullable=False,
        existing_server_default="active",
    )
