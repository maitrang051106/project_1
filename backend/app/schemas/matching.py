from typing import Any
from pydantic import BaseModel, Field

from app.models.enums import TargetCohort, TargetGender, TargetMajorFaculty


class MatchJoinIn(BaseModel):
    target_gender: str = Field(default=TargetGender.ANY.value)
    target_major_faculty: str = Field(default=TargetMajorFaculty.ANY.value)
    target_cohort: str = Field(default=TargetCohort.ANY.value)


class PartnerInfo(BaseModel):
    nickname: str
    gender: str
    cohort: int


class MatchResultOut(BaseModel):
    status: str  # "waiting" | "matched" | "not_found" | "idle"
    attempt_id: str | None = None
    room_id: int | None = None
    partner: PartnerInfo | None = None
    message: str | None = None
    elapsed_seconds: int | None = None
