import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.constants import (
    DEFAULT_AVATAR,
    OTP_COOLDOWN_SECONDS,
    OTP_TTL_SECONDS,
)
from app.core.db import get_db
from app.core.security import (
    create_access_token,
    create_email_hash,
    generate_default_nickname,
    generate_otp,
    hash_otp,
    hash_password,
    is_valid_hust_email,
    normalize_email,
    verify_password,
)
from app.models.enums import UserStatus
from app.models.user import User
from app.services.store import store_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class RequestOtpIn(BaseModel):
    email: str


class RegisterIn(BaseModel):
    email: str
    otp: str
    password: str = Field(min_length=6, description="Password must be at least 6 characters")
    nickname: str | None = None
    avatar: str | None = None


class LoginIn(BaseModel):
    email: str
    password: str


class ResetPasswordIn(BaseModel):
    email: str
    otp: str
    new_password: str = Field(min_length=6, description="Password must be at least 6 characters")


async def _send_otp_email(to_email: str, otp: str, subject_prefix: str = "Verification Code") -> None:
    logger.info("==========================================")
    logger.info(">>> OTP FOR [%s]: %s <<<", to_email, otp)
    logger.info("==========================================")

    try:
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = to_email
        msg["Subject"] = f"[{settings.app_name}] {subject_prefix}: {otp}"
        msg.set_content(
            f"Hello,\n\nYour code is: {otp}\nThis code is valid for 5 minutes. Please do not share it with anyone.\n\nRegards,\n{settings.app_name}"
        )
        await aiosmtplib.send(
            msg,
            hostname=settings.email_host,
            port=settings.email_port,
            timeout=2.0,
        )
    except Exception as e:
        logger.debug("SMTP send failed (offline/dev mock): %s", e)


@router.post("/request-register-otp")
async def request_register_otp(payload: RequestOtpIn, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    norm_email = normalize_email(payload.email)
    if not is_valid_hust_email(norm_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HUST student emails (@sis.hust.edu.vn) are supported.",
        )

    # Check if user already exists with password
    stmt = select(User).where(or_(User.email == norm_email, User.email_hash == create_email_hash(norm_email)))
    res = await db.execute(stmt)
    existing_user = res.scalar_one_or_none()
    if existing_user and existing_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please sign in.",
        )

    email_hash = create_email_hash(norm_email)
    if await store_service.is_in_cooldown(email_hash):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait 60 seconds before requesting a new code.",
        )

    otp = generate_otp()
    otp_h = hash_otp(otp)

    await store_service.set_otp(email_hash, otp_h, ttl=OTP_TTL_SECONDS)
    await store_service.set_cooldown(email_hash, ttl=OTP_COOLDOWN_SECONDS)

    await _send_otp_email(norm_email, otp, subject_prefix="Registration Code")

    return {
        "message": "Verification code sent to your email.",
        "cooldown_seconds": OTP_COOLDOWN_SECONDS,
    }


@router.post("/register")
async def register(
    payload: RegisterIn, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    norm_email = normalize_email(payload.email)
    if not is_valid_hust_email(norm_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HUST student emails (@sis.hust.edu.vn) are supported.",
        )

    email_hash = create_email_hash(norm_email)
    otp_h = hash_otp(payload.otp.strip())

    valid = await store_service.verify_otp(email_hash, otp_h)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    stmt = select(User).where(or_(User.email == norm_email, User.email_hash == email_hash)).options(selectinload(User.profile))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    pwd_hash = hash_password(payload.password)
    chosen_nickname = (payload.nickname or "").strip() or generate_default_nickname()
    avatar = (payload.avatar or "").strip() or DEFAULT_AVATAR

    if not user:
        user = User(
            email=norm_email,
            email_hash=email_hash,
            password_hash=pwd_hash,
            nickname=chosen_nickname,
            avatar=avatar,
            trust_score=100,
        )
        db.add(user)
    else:
        if user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already registered. Please sign in.",
            )
        user.email = norm_email
        user.password_hash = pwd_hash
        user.nickname = chosen_nickname
        user.avatar = avatar
        user.last_login_at = func.now()

    await db.commit()
    await db.refresh(user)

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
            "email": user.email,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "trust_score": user.trust_score,
            "role": user.role.value,
        },
        "has_profile": has_profile,
    }


@router.post("/login")
async def login(
    payload: LoginIn, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    norm_email = normalize_email(payload.email)
    email_hash = create_email_hash(norm_email)

    stmt = select(User).where(or_(User.email == norm_email, User.email_hash == email_hash)).options(selectinload(User.profile))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.status == UserStatus.BANNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended.",
        )

    user.last_login_at = func.now()
    if not user.email:
        user.email = norm_email
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
            "email": user.email,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "trust_score": user.trust_score,
            "role": user.role.value,
        },
        "has_profile": has_profile,
    }


@router.post("/request-reset-otp")
async def request_reset_otp(payload: RequestOtpIn, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    norm_email = normalize_email(payload.email)
    email_hash = create_email_hash(norm_email)

    stmt = select(User).where(or_(User.email == norm_email, User.email_hash == email_hash))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email.",
        )

    if await store_service.is_in_cooldown(email_hash):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait 60 seconds before requesting a new code.",
        )

    otp = generate_otp()
    otp_h = hash_otp(otp)

    await store_service.set_otp(email_hash, otp_h, ttl=OTP_TTL_SECONDS)
    await store_service.set_cooldown(email_hash, ttl=OTP_COOLDOWN_SECONDS)

    await _send_otp_email(norm_email, otp, subject_prefix="Password Reset Code")

    return {
        "message": "Password reset code sent to your email.",
        "cooldown_seconds": OTP_COOLDOWN_SECONDS,
    }


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordIn, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    norm_email = normalize_email(payload.email)
    email_hash = create_email_hash(norm_email)
    otp_h = hash_otp(payload.otp.strip())

    valid = await store_service.verify_otp(email_hash, otp_h)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    stmt = select(User).where(or_(User.email == norm_email, User.email_hash == email_hash)).options(selectinload(User.profile))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email.",
        )

    user.password_hash = hash_password(payload.new_password)
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
        "message": "Password reset successfully.",
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "trust_score": user.trust_score,
            "role": user.role.value,
        },
        "has_profile": has_profile,
    }


# Backwards compatibility for existing test suite or direct OTP verification
@router.post("/request-otp")
async def request_otp(payload: RequestOtpIn, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await request_register_otp(payload, db)


@router.post("/verify-otp")
async def verify_otp(
    payload: dict[str, Any], response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    # If client uses verify-otp without password, create or login with temporary passwordless state
    norm_email = normalize_email(payload.get("email", ""))
    if not is_valid_hust_email(norm_email):
        raise HTTPException(status_code=400, detail="Only @sis.hust.edu.vn is supported.")
    email_hash = create_email_hash(norm_email)
    otp = payload.get("otp", "")
    valid = await store_service.verify_otp(email_hash, hash_otp(otp.strip()))
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")

    stmt = select(User).where(or_(User.email == norm_email, User.email_hash == email_hash)).options(selectinload(User.profile))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        user = User(
            email=norm_email,
            email_hash=email_hash,
            nickname=generate_default_nickname(),
            avatar=DEFAULT_AVATAR,
            trust_score=100,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

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
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "trust_score": user.trust_score,
            "role": user.role.value,
        },
        "has_profile": bool(user.profile is not None),
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
            "email": user.email,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "trust_score": user.trust_score,
            "role": user.role.value,
        },
        "has_profile": has_profile,
        "profile": profile_data,
    }


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Signed out successfully."}
