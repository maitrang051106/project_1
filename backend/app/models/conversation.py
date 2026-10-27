from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ConversationType


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("user_a <> user_b", name="ck_conversations_distinct_users"),
        Index("ix_conversations_user_a", "user_a"),
        Index("ix_conversations_user_b", "user_b"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_a: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_conversations_user_a_users"), nullable=False
    )
    user_b: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_conversations_user_b_users"), nullable=False
    )
    conversation_type: Mapped[ConversationType] = mapped_column(
        "type",
        Enum(
            ConversationType,
            name="conversation_type",
            native_enum=True,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=False,
        default=ConversationType.HUMAN,
        server_default=ConversationType.HUMAN.value,
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    participant_a: Mapped["User"] = relationship(
        back_populates="conversations_as_a", foreign_keys=[user_a]
    )
    participant_b: Mapped["User"] = relationship(
        back_populates="conversations_as_b", foreign_keys=[user_b]
    )
