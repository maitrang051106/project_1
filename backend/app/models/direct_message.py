from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DirectMessage(Base):
    __tablename__ = "direct_messages"
    __table_args__ = (
        Index("ix_direct_messages_sender_id", "sender_id"),
        Index("ix_direct_messages_receiver_id", "receiver_id"),
        Index("ix_direct_messages_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_direct_messages_sender_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    receiver_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_direct_messages_receiver_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    sender: Mapped["User"] = relationship(
        "User", back_populates="sent_direct_messages", foreign_keys=[sender_id]
    )
    receiver: Mapped["User"] = relationship(
        "User", back_populates="received_direct_messages", foreign_keys=[receiver_id]
    )

