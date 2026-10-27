from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.conversation import Conversation
from app.models.enums import (
    ConversationType,
    TargetCohort,
    TargetGender,
    TargetMajorFaculty,
)
from app.models.profile import Profile
from app.models.user import User
from app.services.matching import (
    MatchPreferenceData,
    UserProfileData,
    is_mutual_match,
)
from app.services.store import store_service

router = APIRouter(prefix="/match", tags=["matching"])


class MatchJoinIn(BaseModel):
    target_gender: str = Field(default=TargetGender.ANY.value)
    target_major_faculty: str = Field(default=TargetMajorFaculty.ANY.value)
    target_cohort: str = Field(default=TargetCohort.ANY.value)


@router.post("/join")
async def join_matching(
    payload: MatchJoinIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # 1. Kiểm tra user đã hoàn thành hồ sơ chưa
    stmt = select(Profile).where(Profile.user_id == user.id)
    res = await db.execute(stmt)
    my_profile = res.scalar_one_or_none()

    if not my_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn cần hoàn tất khai báo hồ sơ (Onboarding) trước khi tham gia ghép cặp",
        )

    # 2. Xóa kết quả ghép cũ nếu có
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

    # 3. Quét các ứng viên đang chờ trong hàng đợi
    candidates = await store_service.get_queue_candidates(exclude_user_id=user.id)

    matched_candidate = None
    for cand in candidates:
        cand_prof = UserProfileData(**cand["profile"])
        cand_pref = MatchPreferenceData(**cand["pref"])

        if is_mutual_match(my_profile_data, my_pref_data, cand_prof, cand_pref):
            matched_candidate = cand
            break

    # 4. Nếu tìm thấy người thỏa mãn 3 ràng buộc hai chiều
    if matched_candidate:
        cand_user_id = matched_candidate["user_id"]
        # Xóa người đó khỏi hàng đợi
        await store_service.remove_from_queue(cand_user_id)

        # Lấy thông tin đối phương để hiển thị
        cand_user_res = await db.execute(
            select(User).where(User.id == cand_user_id).options(selectinload(User.profile))
        )
        cand_user = cand_user_res.scalar_one_or_none()
        cand_nickname = cand_user.nickname if cand_user else "Anonymous Partner"

        # Tạo Conversation trong Database
        conv = Conversation(
            user_a=user.id,
            user_b=cand_user_id,
            type=ConversationType.HUMAN,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        # Lưu thông báo kết quả cho cả 2 phía
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

    # 5. Nếu chưa có ai phù hợp, đưa vào hàng đợi
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

    return {"status": "waiting", "message": "Đang tìm kiếm người phù hợp theo 3 tiêu chí của bạn..."}


@router.get("/status")
async def get_matching_status(user: User = Depends(get_current_user)) -> dict[str, Any]:
    # Kiểm tra xem có người vừa ghép đôi thành công với mình chưa
    match_result = await store_service.get_match_result(user.id)
    if match_result:
        return {
            "status": "matched",
            "room_id": match_result["room_id"],
            "partner": match_result.get("partner"),
        }

    # Kiểm tra xem user có đang nằm trong hàng đợi không
    candidates = await store_service.get_queue_candidates(exclude_user_id=-1)
    is_waiting = any(c["user_id"] == user.id for c in candidates)

    if is_waiting:
        return {"status": "waiting"}

    return {"status": "idle"}


@router.post("/leave")
async def leave_matching(user: User = Depends(get_current_user)) -> dict[str, str]:
    await store_service.remove_from_queue(user.id)
    await store_service.clear_match_result(user.id)
    return {"message": "Đã rời khỏi hàng đợi tìm kiếm"}

