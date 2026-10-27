from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_profiles_user_id_users"
        ),
        primary_key=True,
    )
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    faculty_code: Mapped[str] = mapped_column(String(20), nullable=False)
    major_code: Mapped[str] = mapped_column(String(20), nullable=False)
    cohort: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    user: Mapped["User"] = relationship(back_populates="profile")
