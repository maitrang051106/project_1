from pydantic import BaseModel, Field

from app.core.constants import MAX_COHORT, MIN_COHORT


class ProfileSubmitIn(BaseModel):
    gender: str = Field(..., description="'male' or 'female'")
    major_code: str = Field(..., description="HUST major code, e.g. 'IT1', 'EE2'")
    cohort: int = Field(
        ...,
        ge=MIN_COHORT,
        le=MAX_COHORT,
        description=f"Student cohort, from K{MIN_COHORT} to K{MAX_COHORT}",
    )
    nickname: str | None = Field(default=None, description="Custom nickname")
    avatar: str | None = Field(default=None, description="Custom avatar emoji")


class ProfileOut(BaseModel):
    user_id: int
    gender: str
    faculty_code: str
    faculty_name: str
    major_code: str
    major_name: str
    cohort: int
    updated_at: str
