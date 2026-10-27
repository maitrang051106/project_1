from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.enums import Gender
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileSubmitIn
from app.services.catalog import get_all_majors, get_major_by_code

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/catalog")
async def get_catalog() -> list[dict[str, Any]]:
    """Retrieve 68 HUST majors catalog."""
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
            detail="User profile not completed yet.",
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
    raw_gender = payload.gender.strip().lower()
    if raw_gender == Gender.MALE.value:
        gender = Gender.MALE.value
    elif raw_gender == Gender.FEMALE.value:
        gender = Gender.FEMALE.value
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gender must be 'male' or 'female'.",
        )

    major_code = payload.major_code.strip().upper()
    major_info = get_major_by_code(major_code)
    if not major_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Major code '{major_code}' not found in HUST catalog.",
        )

    faculty_code = major_info["faculty_code"]

    # Update nickname and avatar if provided
    chosen_name = (payload.nickname or "").strip()
    if chosen_name:
        user.nickname = chosen_name
    if payload.avatar and payload.avatar.strip():
        user.avatar = payload.avatar.strip()

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

    return {
        "message": "Profile updated successfully.",
        "profile": {
            "gender": profile.gender,
            "faculty_code": profile.faculty_code,
            "major_code": profile.major_code,
            "cohort": profile.cohort,
        },
        "user": {
            "nickname": user.nickname,
            "avatar": user.avatar,
        },
    }
