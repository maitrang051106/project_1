import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.core.security import (
    create_access_token,
    create_email_hash,
    generate_anon_name,
    generate_otp,
    hash_otp,
    is_valid_hust_email,
    normalize_email,
)
from app.models.user import User
from app.services.store import store_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class RequestOtpIn(BaseModel):
    email: str


class VerifyOtpIn(BaseModel):
    email: str
    otp: str


@router.post("/request-otp")
async def request_otp(payload: RequestOtpIn) -> dict[str, Any]:
    norm_email = normalize_email(payload.email)
    if not is_valid_hust_email(norm_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ chấp nhận email sinh viên/cán bộ HUST (@hust.edu.vn hoặc @sis.hust.edu.vn)",
        )

    email_hash = create_email_hash(norm_email)
    if await store_service.is_in_cooldown(email_hash):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Vui lòng đợi 60 giây trước khi yêu cầu mã OTP mới",
        )

    otp = generate_otp()
    otp_h = hash_otp(otp)

    await store_service.set_otp(email_hash, otp_h, ttl=300)
    await store_service.set_cooldown(email_hash, ttl=60)

    # In log nổi bật để dễ dàng copy test khi dev / production
    logger.info("==========================================")
    logger.info(">>> MÃ OTP ĐĂNG NHẬP CHO [%s]: %s <<<", norm_email, otp)
    logger.info("==========================================")

    # Gửi qua SMTP nếu có Mailpit / SMTP server
    try:
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = norm_email
        msg["Subject"] = f"[{settings.app_name}] Mã OTP đăng nhập: {otp}"
        msg.set_content(
            f"Chào bạn,\n\nMã OTP của bạn là: {otp}\nMã có hiệu lực trong 5 phút. Vui lòng không chia sẻ mã này cho bất kỳ ai.\n\nTrân trọng,\n{settings.app_name}"
        )
        await aiosmtplib.send(
            msg,
            hostname=settings.email_host,
            port=settings.email_port,
            timeout=2.0,
        )
    except Exception as e:
        logger.debug("SMTP not reachable (local dev/mock): %s", e)

    return {
        "message": "Mã OTP đã được gửi về email của bạn (vui lòng kiểm tra hộp thư)",
        "cooldown_seconds": 60,
    }


@router.post("/verify-otp")
async def verify_otp(
    payload: VerifyOtpIn, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    norm_email = normalize_email(payload.email)
    email_hash = create_email_hash(norm_email)
    otp_h = hash_otp(payload.otp.strip())

    valid = await store_service.verify_otp(email_hash, otp_h)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không chính xác hoặc đã hết hạn (tối đa 5 lần thử sai)",
        )

    stmt = select(User).where(User.email_hash == email_hash).options(selectinload(User.profile))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        user = User(
            email_hash=email_hash,
            anon_name=generate_anon_name(),
            trust_score=100,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.last_login_at = func.now()
        await db.commit()

    token = create_access_token({"sub": str(user.id)})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_expire_seconds,
        path="/",
    )

    has_profile = bool(user.profile is not None)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "anon_name": user.anon_name,
            "trust_score": user.trust_score,
            "role": user.role.value,
        },
        "has_profile": has_profile,
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    has_profile = bool(user.profile is not None)
    profile_data = None
    if has_profile and user.profile:
        profile_data = {
            "gender": user.profile.gender,
            "faculty_code": user.profile.faculty_code,
            "major_code": user.profile.major_code,
            "cohort": user.profile.cohort,
        }

    return {
        "user": {
            "id": user.id,
            "anon_name": user.anon_name,
            "trust_score": user.trust_score,
            "role": user.role.value,
        },
        "has_profile": has_profile,
        "profile": profile_data,
    }


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Đã đăng xuất thành công"}
