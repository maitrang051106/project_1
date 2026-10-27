from datetime import datetime

from sqlalchemy import (
    CHAR,
    DateTime,
    Enum,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DEFAULT_AVATAR
from app.models.base import Base
from app.models.enums import UserRole, UserStatus


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email_hash", name="uq_users_email_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(191), unique=True, index=True, nullable=True)
    email_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    anon_name: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar: Mapped[str] = mapped_column(String(20), nullable=False, default=DEFAULT_AVATAR, server_default=text(f"'{DEFAULT_AVATAR}'"))
    trust_score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default=text("100")
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            name="user_status",
            native_enum=True,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=True,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    profile: Mapped["Profile | None"] = relationship(
        back_populates="user", uselist=False
    )
    conversations_as_a: Mapped[list["Conversation"]] = relationship(
        back_populates="participant_a", foreign_keys="Conversation.user_a"
    )
    conversations_as_b: Mapped[list["Conversation"]] = relationship(
        back_populates="participant_b", foreign_keys="Conversation.user_b"
    )
    friendships_as_a: Mapped[list["Friendship"]] = relationship(
        "Friendship", back_populates="friend_a", foreign_keys="Friendship.user_a"
    )
    friendships_as_b: Mapped[list["Friendship"]] = relationship(
        "Friendship", back_populates="friend_b", foreign_keys="Friendship.user_b"
    )
    sent_direct_messages: Mapped[list["DirectMessage"]] = relationship(
        "DirectMessage", back_populates="sender", foreign_keys="DirectMessage.sender_id"
    )
    received_direct_messages: Mapped[list["DirectMessage"]] = relationship(
        "DirectMessage", back_populates="receiver", foreign_keys="DirectMessage.receiver_id"
    )
