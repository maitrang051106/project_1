import secrets
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.constants import MATCH_TIMEOUT_SECONDS
from app.core.db import get_db
from app.models.conversation import Conversation
from app.models.enums import ConversationType, UserStatus
from app.models.profile import Profile
from app.models.user import User
from app.schemas.matching import MatchJoinIn, MatchResultOut
from app.services.matching import (
    MatchPreferenceData,
    UserProfileData,
    daily_match_limit,
    is_mutual_match,
    vietnam_day_utc_window,
)
from app.services.store import store_service

router = APIRouter(prefix="/match", tags=["matching"])


async def _daily_conversation_count(
    db: AsyncSession, user_id: int, day_start: Any, day_end: Any
) -> int:
    result = await db.execute(
        select(Conversation.id)
        .where(
            or_(Conversation.user_a == user_id, Conversation.user_b == user_id),
            Conversation.started_at >= day_start,
            Conversation.started_at < day_end,
        )
        .with_for_update()
    )
    return len(result.scalars().all())


async def _has_active_conversation(db: AsyncSession, user_id: int) -> bool:
    result = await db.execute(
        select(Conversation.id)
        .where(
            or_(Conversation.user_a == user_id, Conversation.user_b == user_id),
            Conversation.ended_at.is_(None),
        )
        .limit(1)
        .with_for_update()
    )
    return result.scalar_one_or_none() is not None


@router.post("/join", response_model=MatchResultOut)
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

    # 2. Clear any previous match result, terminal state, or stale queue entry
    await store_service.clear_match_result(user.id)
    await store_service.remove_from_queue(user.id)

    attempt_id = secrets.token_hex(8)

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

    day_start, day_end = vietnam_day_utc_window()
    quota = daily_match_limit(user.trust_score)
    if quota == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your trust score does not currently allow matching.",
        )
    if await _has_active_conversation(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active conversation.",
        )
    if quota is not None and await _daily_conversation_count(
        db, user.id, day_start, day_end
    ) >= quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You have reached today's matching limit.",
        )

    # 3. Scan active candidates waiting in queue
    candidates = await store_service.get_queue_candidates(exclude_user_id=user.id)

    matched_candidate = None
    for cand in candidates:
        cand_prof = UserProfileData(**cand["profile"])
        cand_pref = MatchPreferenceData(**cand["pref"])

        if is_mutual_match(my_profile_data, my_pref_data, cand_prof, cand_pref):
            cand_user_id = cand["user_id"]
            # 4. Concurrency Protection: Atomically reserve candidate from queue
            reserved = await store_service.reserve_candidate(cand_user_id)
            if not reserved:
                # Candidate was claimed by another concurrent match; continue search
                continue

            matched_candidate = cand
            break

    # 5. If mutual match was found and atomically reserved
    if matched_candidate:
        cand_user_id = matched_candidate["user_id"]

        try:
            locked_users_res = await db.execute(
                select(User)
                .where(User.id.in_([user.id, cand_user_id]))
                .order_by(User.id)
                .with_for_update()
            )
            locked_users = {row.id: row for row in locked_users_res.scalars().all()}
            current_user = locked_users.get(user.id)
            cand_user = locked_users.get(cand_user_id)
            current_has_active = False
            candidate_has_active = False
            if not current_user or not cand_user:
                await store_service.remove_from_queue(cand_user_id)
                await db.rollback()
                matched_candidate = None
            elif (
                current_user.status == UserStatus.BANNED
                or current_user.trust_score <= 0
            ):
                await store_service.restore_queue_entry(matched_candidate)
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your account is not eligible for matching.",
                )
            elif cand_user.status == UserStatus.BANNED or cand_user.trust_score <= 0:
                await store_service.remove_from_queue(cand_user_id)
                await db.rollback()
                matched_candidate = None
            else:
                current_has_active = await _has_active_conversation(db, user.id)
                candidate_has_active = await _has_active_conversation(db, cand_user_id)

            if current_user and cand_user and current_has_active:
                if candidate_has_active:
                    await store_service.remove_from_queue(cand_user_id)
                else:
                    await store_service.restore_queue_entry(matched_candidate)
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You already have an active conversation.",
                )
            elif current_user and cand_user and candidate_has_active:
                await store_service.remove_from_queue(cand_user_id)
                await db.rollback()
                matched_candidate = None
            elif current_user and cand_user:
                current_quota = daily_match_limit(current_user.trust_score)
                candidate_quota = daily_match_limit(cand_user.trust_score)
                current_count = await _daily_conversation_count(
                    db, user.id, day_start, day_end
                )
                candidate_count = await _daily_conversation_count(
                    db, cand_user_id, day_start, day_end
                )

                if current_quota is not None and current_count >= current_quota:
                    await store_service.restore_queue_entry(matched_candidate)
                    await db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="You have reached today's matching limit.",
                    )
                if candidate_quota is not None and candidate_count >= candidate_quota:
                    await store_service.remove_from_queue(cand_user_id)
                    await db.rollback()
                    matched_candidate = None

            if matched_candidate is None:
                cand_user = None
            else:
                cand_nickname = cand_user.nickname

                conv = Conversation(
                    user_a=user.id,
                    user_b=cand_user_id,
                    type=ConversationType.HUMAN,
                )
                db.add(conv)
                await db.commit()
                await db.refresh(conv)
        except HTTPException:
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            await store_service.restore_queue_entry(matched_candidate)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create conversation session. Please try again.",
            ) from exc

        if matched_candidate is None:
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
                attempt_id=attempt_id,
            )
            return {
                "status": "waiting",
                "attempt_id": attempt_id,
                "message": "Searching for a partner matching your 3 criteria...",
            }

        cand_attempt_id = matched_candidate.get("attempt_id", "")
        # Store match results in Redis/Store for both participants
        await store_service.save_match_result(
            user_a_id=user.id,
            user_b_id=cand_user_id,
            room_id=conv.id,
            partner_a_info={
                "nickname": cand_nickname,
                "gender": matched_candidate["profile"]["gender"],
                "cohort": matched_candidate["profile"]["cohort"],
            },
            partner_b_info={
                "nickname": user.nickname,
                "gender": my_profile.gender,
                "cohort": my_profile.cohort,
            },
            attempt_a_id=attempt_id,
            attempt_b_id=cand_attempt_id,
        )

        return {
            "status": "matched",
            "attempt_id": attempt_id,
            "room_id": conv.id,
            "partner": {
                "nickname": cand_nickname,
                "gender": matched_candidate["profile"]["gender"],
                "cohort": matched_candidate["profile"]["cohort"],
            },
        }

    # 6. If no candidate matches, add user to waiting queue with 60s TTL
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
        attempt_id=attempt_id,
    )

    return {
        "status": "waiting",
        "attempt_id": attempt_id,
        "message": "Searching for a partner matching your 3 criteria...",
    }


@router.get("/status", response_model=MatchResultOut)
async def get_matching_status(
    attempt_id: str | None = Query(default=None),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    # 1. Check if someone matched with user
    match_result = await store_service.get_match_result(user.id)
    if match_result:
        return {
            "status": "matched",
            "attempt_id": match_result.get("attempt_id"),
            "room_id": match_result["room_id"],
            "partner": match_result.get("partner"),
        }

    # 2. Check if user has a terminal not_found result (60s expired)
    not_found = await store_service.get_not_found_result(user.id)
    if not_found:
        return {
            "status": "not_found",
            "attempt_id": not_found.get("attempt_id"),
            "message": "No matching peer found within 60 seconds.",
        }

    # 3. Check if user is currently in the waiting queue
    queue_entry = await store_service.get_queue_entry(user.id)
    if queue_entry:
        now = time.time()
        elapsed = now - queue_entry["joined_at"]
        if elapsed >= MATCH_TIMEOUT_SECONDS:
            # Reached 60s deadline -> mark not_found and evict from queue
            await store_service.remove_from_queue(user.id)
            entry_attempt_id = queue_entry.get("attempt_id", "")
            await store_service.save_not_found_result(user.id, entry_attempt_id)
            return {
                "status": "not_found",
                "attempt_id": entry_attempt_id,
                "message": "No matching peer found within 60 seconds.",
            }

        return {
            "status": "waiting",
            "attempt_id": queue_entry.get("attempt_id"),
            "elapsed_seconds": int(elapsed),
        }

    return {"status": "idle"}


@router.post("/leave")
async def leave_matching(user: User = Depends(get_current_user)) -> dict[str, str]:
    await store_service.remove_from_queue(user.id)
    await store_service.clear_match_result(user.id)
    return {"message": "Left the matching queue."}
