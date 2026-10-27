from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.conversation import Conversation
from app.models.enums import ConversationType
from app.models.profile import Profile
from app.models.user import User
from app.schemas.matching import MatchJoinIn
from app.services.matching import (
    MatchPreferenceData,
    UserProfileData,
    is_mutual_match,
)
from app.services.store import store_service

router = APIRouter(prefix="/match", tags=["matching"])


@router.post("/join")
async def join_matching(
    payload: MatchJoinIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # 1. Verify user has completed onboarding profile
    stmt = select(Profile).where(Profile.user_id == user.id)
    res = await db.execute(stmt)
    my_profile = res.scalar_one_or_none()

    if not my_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete your profile (Onboarding) before joining matchmaking.",
        )

    # 2. Clear previous match result if any
    await store_service.clear_match_result(user.id)

    my_profile_data = UserProfileData(
        user_id=user.id,
        gender=my_profile.gender,
        faculty_code=my_profile.faculty_code,
        major_code=my_profile.major_code,
        cohort=my_profile.cohort,
    )

    my_pref_data = MatchPreferenceData(
        target_gender=payload.target_gender,
        target_major_faculty=payload.target_major_faculty,
        target_cohort=payload.target_cohort,
    )

    # 3. Scan candidates waiting in queue
    candidates = await store_service.get_queue_candidates(exclude_user_id=user.id)

    matched_candidate = None
    for cand in candidates:
        cand_prof = UserProfileData(**cand["profile"])
        cand_pref = MatchPreferenceData(**cand["pref"])

        if is_mutual_match(my_profile_data, my_pref_data, cand_prof, cand_pref):
            matched_candidate = cand
            break

    # 4. If a mutual match satisfying all 3 hard constraints is found
    if matched_candidate:
        cand_user_id = matched_candidate["user_id"]
        # Remove matched user from queue
        await store_service.remove_from_queue(cand_user_id)

        # Retrieve opponent info
        cand_user_res = await db.execute(
            select(User).where(User.id == cand_user_id).options(selectinload(User.profile))
        )
        cand_user = cand_user_res.scalar_one_or_none()
        cand_nickname = cand_user.nickname if cand_user else "Anonymous Partner"

        # Create Conversation in Database
        conv = Conversation(
            user_a=user.id,
            user_b=cand_user_id,
            type=ConversationType.HUMAN,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        # Store match result notification for both participants
        await store_service.save_match_result(
            user_a_id=user.id,
            user_b_id=cand_user_id,
            room_id=conv.id,
            partner_a_info={"nickname": cand_nickname, "gender": cand_prof.gender, "cohort": cand_prof.cohort},
            partner_b_info={"nickname": user.nickname, "gender": my_profile.gender, "cohort": my_profile.cohort},
        )

        return {
            "status": "matched",
            "room_id": conv.id,
            "partner": {
                "nickname": cand_nickname,
                "gender": cand_prof.gender,
                "cohort": cand_prof.cohort,
            },
        }

    # 5. If no candidate matches, add user to waiting queue
    await store_service.add_to_queue(
        user_id=user.id,
        profile={
            "user_id": user.id,
            "gender": my_profile.gender,
            "faculty_code": my_profile.faculty_code,
            "major_code": my_profile.major_code,
            "cohort": my_profile.cohort,
        },
        pref={
            "target_gender": payload.target_gender,
            "target_major_faculty": payload.target_major_faculty,
            "target_cohort": payload.target_cohort,
        },
    )

    return {"status": "waiting", "message": "Searching for a partner matching your 3 criteria..."}


@router.get("/status")
async def get_matching_status(user: User = Depends(get_current_user)) -> dict[str, Any]:
    # Check if someone matched with user
    match_result = await store_service.get_match_result(user.id)
    if match_result:
        return {
            "status": "matched",
            "room_id": match_result["room_id"],
            "partner": match_result.get("partner"),
        }

    # Check if user is currently in the waiting queue
    candidates = await store_service.get_queue_candidates(exclude_user_id=-1)
    is_waiting = any(c["user_id"] == user.id for c in candidates)

    if is_waiting:
        return {"status": "waiting"}

    return {"status": "idle"}


@router.post("/leave")
async def leave_matching(user: User = Depends(get_current_user)) -> dict[str, str]:
    await store_service.remove_from_queue(user.id)
    await store_service.clear_match_result(user.id)
    return {"message": "Left the matching queue."}

