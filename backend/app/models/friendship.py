from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("user_a", "user_b", name="uq_friendships_user_a_user_b"),
        Index("ix_friendships_user_a", "user_a"),
        Index("ix_friendships_user_b", "user_b"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_a: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_friendships_user_a_users", ondelete="CASCADE"),
        nullable=False,
    )
    user_b: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_friendships_user_b_users", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", name="fk_friendships_requested_by_users", ondelete="CASCADE"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="accepted"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    friend_a: Mapped["User"] = relationship(
        "User", back_populates="friendships_as_a", foreign_keys=[user_a]
    )
    friend_b: Mapped["User"] = relationship(
        "User", back_populates="friendships_as_b", foreign_keys=[user_b]
    )

    def can_be_responded_to_by(self, responder_id: int, requester_id: int) -> bool:
        return (
            self.status == "pending"
            and self.requested_by == requester_id
            and responder_id != requester_id
            and {self.user_a, self.user_b} == {responder_id, requester_id}
        )

