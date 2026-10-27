"""Add email, password_hash, avatar to users, add friendships and direct_messages tables.

Revision ID: 0003_auth_email_friends_dms
Revises: 0002_remove_shadowban_status
Create Date: 2026-10-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_auth_email_friends_dms"
down_revision: Union[str, None] = "0002_remove_shadowban_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add email, password_hash, avatar to users
    op.add_column("users", sa.Column("email", sa.String(191), nullable=True))
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])

    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("avatar", sa.String(20), nullable=False, server_default="🦉"))

    # 2. Create friendships table
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

    # 3. Create direct_messages table
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
    op.drop_column("users", "avatar")
    op.drop_column("users", "password_hash")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_index("ix_users_email", "users")
    op.drop_column("users", "email")

