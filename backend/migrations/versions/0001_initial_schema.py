"""Create initial users, profiles, and conversations tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("anon_name", sa.String(length=50), nullable=False),
        sa.Column(
            "trust_score", sa.Integer(), server_default=sa.text("100"), nullable=False
        ),
        sa.Column(
            "status",
            mysql.ENUM("active", "shadowban", "banned", name="user_status"),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "role",
            mysql.ENUM("user", "admin", name="user_role"),
            server_default="user",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_hash", name="uq_users_email_hash"),
    )
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("gender", sa.String(length=10), nullable=False),
        sa.Column("faculty_code", sa.String(length=20), nullable=False),
        sa.Column("major_code", sa.String(length=20), nullable=False),
        sa.Column("cohort", sa.Integer(), nullable=False),



        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_a", sa.Integer(), nullable=False),
        sa.Column("user_b", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            mysql.ENUM("human", "bot", name="conversation_type"),
            server_default="human",
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "user_a <> user_b", name="ck_conversations_distinct_users"
        ),
        sa.ForeignKeyConstraint(
            ["user_a"], ["users.id"], name="fk_conversations_user_a_users"
        ),
        sa.ForeignKeyConstraint(
            ["user_b"], ["users.id"], name="fk_conversations_user_b_users"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_a", "conversations", ["user_a"])
    op.create_index("ix_conversations_user_b", "conversations", ["user_b"])


def downgrade() -> None:
    op.drop_index("ix_conversations_user_b", table_name="conversations")
    op.drop_index("ix_conversations_user_a", table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("profiles")
    op.drop_table("users")
