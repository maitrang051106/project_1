from typing import Any
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import (
    DEFAULT_AVATAR,
    OTP_COOLDOWN_SECONDS,
    OTP_TTL_SECONDS,
)
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
from app.schemas.auth import LoginIn, RegisterIn, ResetPasswordIn
from app.services.email_service import send_otp_email
from app.services.store import store_service


class AuthService:
    @staticmethod
    async def request_register_otp(email: str, db: AsyncSession) -> dict[str, Any]:
        norm_email = normalize_email(email)
        if not is_valid_hust_email(norm_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only HUST student emails (@sis.hust.edu.vn) are supported.",
            )

        # Query user directly by email
        stmt = select(User).where(User.email == norm_email)
        res = await db.execute(stmt)
        existing_user = res.scalar_one_or_none()
        if existing_user and existing_user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists. Please sign in.",
            )

        email_key = norm_email
        if await store_service.is_in_cooldown(email_key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {OTP_COOLDOWN_SECONDS} seconds before requesting a new code.",
            )

        otp = generate_otp()
        otp_h = hash_otp(otp)

        await store_service.set_otp(email_key, otp_h, ttl=OTP_TTL_SECONDS)
        await store_service.set_cooldown(email_key, ttl=OTP_COOLDOWN_SECONDS)

        await send_otp_email(norm_email, otp, subject_prefix="Registration Code")

        return {
            "message": "Verification code sent to your email.",
            "cooldown_seconds": OTP_COOLDOWN_SECONDS,
        }

    @staticmethod
    async def register(payload: RegisterIn, db: AsyncSession) -> tuple[str, User, bool]:
        norm_email = normalize_email(payload.email)
        if not is_valid_hust_email(norm_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only HUST student emails (@sis.hust.edu.vn) are supported.",
            )

        email_key = norm_email
        otp_h = hash_otp(payload.otp.strip())

        valid = await store_service.verify_otp(email_key, otp_h)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code.",
            )

        stmt = (
            select(User)
            .where(User.email == norm_email)
            .options(selectinload(User.profile))
        )
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()

        pwd_hash = hash_password(payload.password)
        chosen_nickname = (payload.nickname or "").strip() or generate_default_nickname()
        avatar = (payload.avatar or "").strip() or DEFAULT_AVATAR
        email_hash = create_email_hash(norm_email)

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
            user.password_hash = pwd_hash
            user.nickname = chosen_nickname
            user.avatar = avatar
            user.last_login_at = func.now()

        await db.commit()
        await db.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        has_profile = bool(user.profile is not None)
        return token, user, has_profile

    @staticmethod
    async def login(payload: LoginIn, db: AsyncSession) -> tuple[str, User, bool]:
        norm_email = normalize_email(payload.email)

        stmt = (
            select(User)
            .where(User.email == norm_email)
            .options(selectinload(User.profile))
        )
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
        await db.commit()

        token = create_access_token({"sub": str(user.id)})
        has_profile = bool(user.profile is not None)
        return token, user, has_profile

    @staticmethod
    async def request_reset_otp(email: str, db: AsyncSession) -> dict[str, Any]:
        norm_email = normalize_email(email)

        stmt = select(User).where(User.email == norm_email)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email.",
            )

        email_key = norm_email
        if await store_service.is_in_cooldown(email_key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {OTP_COOLDOWN_SECONDS} seconds before requesting a new code.",
            )

        otp = generate_otp()
        otp_h = hash_otp(otp)

        await store_service.set_otp(email_key, otp_h, ttl=OTP_TTL_SECONDS)
        await store_service.set_cooldown(email_key, ttl=OTP_COOLDOWN_SECONDS)

        await send_otp_email(norm_email, otp, subject_prefix="Password Reset Code")

        return {
            "message": "Password reset code sent to your email.",
            "cooldown_seconds": OTP_COOLDOWN_SECONDS,
        }

    @staticmethod
    async def reset_password(
        payload: ResetPasswordIn, db: AsyncSession
    ) -> tuple[str, User, bool]:
        norm_email = normalize_email(payload.email)
        email_key = norm_email
        otp_h = hash_otp(payload.otp.strip())

        valid = await store_service.verify_otp(email_key, otp_h)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code.",
            )

        stmt = (
            select(User)
            .where(User.email == norm_email)
            .options(selectinload(User.profile))
        )
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
        has_profile = bool(user.profile is not None)
        return token, user, has_profile
