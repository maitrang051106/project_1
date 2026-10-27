"""Unified initial database schema.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-10-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("email", sa.String(191), nullable=True),
        sa.Column("email_hash", sa.CHAR(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("nickname", sa.String(50), nullable=False),
        sa.Column("avatar", sa.String(20), nullable=False, server_default="🦉"),
        sa.Column("trust_score", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column(
            "status",
            mysql.ENUM("active", "banned", name="user_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "role",
            mysql.ENUM("user", "admin", name="user_role"),
            nullable=False,
            server_default="user",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("email_hash", name="uq_users_email_hash"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # 2. profiles table
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("gender", sa.String(10), nullable=False),
        sa.Column("faculty_code", sa.String(20), nullable=False),
        sa.Column("major_code", sa.String(20), nullable=False),
        sa.Column("cohort", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_profiles_user_id_users", ondelete="CASCADE"),
    )

    # 3. conversations table
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("user_a", sa.Integer(), nullable=False),
        sa.Column("user_b", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            mysql.ENUM("human", "bot", name="conversation_type"),
            nullable=False,
            server_default="human",
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("user_a <> user_b", name="ck_conversations_distinct_users"),
        sa.ForeignKeyConstraint(["user_a"], ["users.id"], name="fk_conversations_user_a_users"),
        sa.ForeignKeyConstraint(["user_b"], ["users.id"], name="fk_conversations_user_b_users"),
    )
    op.create_index("ix_conversations_user_a", "conversations", ["user_a"])
    op.create_index("ix_conversations_user_b", "conversations", ["user_b"])

    # 4. friendships table
    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("user_a", sa.Integer(), nullable=False),
        sa.Column("user_b", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="accepted"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(["user_a"], ["users.id"], name="fk_friendships_user_a_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_b"], ["users.id"], name="fk_friendships_user_b_users", ondelete="CASCADE"),
        sa.UniqueConstraint("user_a", "user_b", name="uq_friendships_user_a_user_b"),
    )
    op.create_index("ix_friendships_user_a", "friendships", ["user_a"])
    op.create_index("ix_friendships_user_b", "friendships", ["user_b"])

    # 5. direct_messages table
    op.create_table(
        "direct_messages",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("receiver_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], name="fk_direct_messages_sender_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], name="fk_direct_messages_receiver_id_users", ondelete="CASCADE"),
    )
    op.create_index("ix_direct_messages_sender_id", "direct_messages", ["sender_id"])
    op.create_index("ix_direct_messages_receiver_id", "direct_messages", ["receiver_id"])
    op.create_index("ix_direct_messages_created_at", "direct_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("direct_messages")
    op.drop_table("friendships")
    op.drop_table("conversations")
    op.drop_table("profiles")
    op.drop_table("users")

