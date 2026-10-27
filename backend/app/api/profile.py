from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.enums import Gender
from app.models.profile import Profile
from app.models.user import User
from app.services.catalog import get_all_majors, get_major_by_code

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileSubmitIn(BaseModel):
    gender: str = Field(..., description="'nam' hoặc 'nu'")
    major_code: str = Field(..., description="Mã ngành HUST, ví dụ 'IT1', 'EE2'")
    cohort: int = Field(..., ge=63, le=71, description="Khóa sinh viên, từ K63 đến K71")


@router.get("/catalog")
async def get_catalog() -> list[dict[str, Any]]:
    """Lấy danh mục 68 ngành học và các Trường/Viện trực thuộc HUST."""
    return get_all_majors()


@router.get("/me")
async def get_my_profile(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    stmt = select(Profile).where(Profile.user_id == user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng chưa hoàn thành khai báo hồ sơ (Onboarding)",
        )

    major_info = get_major_by_code(profile.major_code)
    major_name = major_info["major_name"] if major_info else profile.major_code
    faculty_name = major_info["faculty_name"] if major_info else profile.faculty_code

    return {
        "user_id": profile.user_id,
        "gender": profile.gender,
        "faculty_code": profile.faculty_code,
        "faculty_name": faculty_name,
        "major_code": profile.major_code,
        "major_name": major_name,
        "cohort": profile.cohort,
        "updated_at": profile.updated_at.isoformat(),
    }


@router.post("")
async def create_or_update_profile(
    payload: ProfileSubmitIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    gender = payload.gender.strip().lower()
    if gender not in (Gender.NAM.value, Gender.NU.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giới tính chỉ chấp nhận 'nam' hoặc 'nu'",
        )

    major_code = payload.major_code.strip().upper()
    major_info = get_major_by_code(major_code)
    if not major_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã ngành '{major_code}' không tồn tại trong danh mục 68 ngành HUST",
        )

    faculty_code = major_info["faculty_code"]

    stmt = select(Profile).where(Profile.user_id == user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = Profile(
            user_id=user.id,
            gender=gender,
            faculty_code=faculty_code,
            major_code=major_code,
            cohort=payload.cohort,
        )
        db.add(profile)
    else:
        profile.gender = gender
        profile.faculty_code = faculty_code
        profile.major_code = major_code
        profile.cohort = payload.cohort

    await db.commit()
    await db.refresh(profile)

    return {
        "message": "Cập nhật hồ sơ thành công",
        "profile": {
            "user_id": profile.user_id,
            "gender": profile.gender,
            "faculty_code": profile.faculty_code,
            "faculty_name": major_info["faculty_name"],
            "major_code": profile.major_code,
            "major_name": major_info["major_name"],
            "cohort": profile.cohort,
        },
    }

