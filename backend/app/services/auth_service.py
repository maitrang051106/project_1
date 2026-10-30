import logging
import time
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.constants import (
    DEFAULT_AVATAR,
    OTP_COOLDOWN_SECONDS,
    OTP_TTL_SECONDS,
)
from app.core.security import (
    create_access_token,
    create_email_hash,
    decode_access_token,
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

logger = logging.getLogger(__name__)

GENERIC_OTP_SENT_MESSAGE = "Nếu địa chỉ hợp lệ, mã xác nhận sẽ được gửi."


class AuthService:
    @staticmethod
    async def _issue_session_token(user_id: int) -> str:
        token = create_access_token({"sub": str(user_id)})
        claims = decode_access_token(token)
        if not claims or not claims.get("jti") or not claims.get("exp"):
            raise RuntimeError("Failed to create a valid authentication token.")

        ttl = max(1, int(claims["exp"] - time.time()))
        await store_service.create_session(user_id, claims["jti"], ttl)
        return token

    @staticmethod
    async def request_register_otp(email: str, client_ip: str, db: AsyncSession) -> dict[str, Any]:
        norm_email = normalize_email(email)
        if not is_valid_hust_email(norm_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only HUST student emails (@sis.hust.edu.vn) are supported.",
            )

        # 1. IP Rate limit check
        if not await store_service.check_rate_limit(
            f"ip:{client_ip}",
            settings.rate_limit_ip_requests,
            settings.rate_limit_ip_window_seconds,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests from this IP address. Please try again later.",
            )

        email_hash = create_email_hash(norm_email)

        # 2. Email Rate limit check (using HMAC, never raw email)
        if not await store_service.check_rate_limit(
            f"email:{email_hash}",
            settings.rate_limit_email_requests,
            settings.rate_limit_email_window_seconds,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests for this email address. Please try again later.",
            )

        # 3. Cooldown check
        if await store_service.is_in_cooldown(email_hash, purpose="register"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {OTP_COOLDOWN_SECONDS} seconds before requesting a new code.",
            )

        # 4. Check if account already exists with a password
        stmt = select(User).where(User.email == norm_email)
        res = await db.execute(stmt)
        existing_user = res.scalar_one_or_none()

        if existing_user and existing_user.password_hash:
            # Prevent account enumeration: do not send email, but return generic success response
            await store_service.set_cooldown(email_hash, purpose="register", ttl=OTP_COOLDOWN_SECONDS)
            return {
                "message": GENERIC_OTP_SENT_MESSAGE,
                "cooldown_seconds": OTP_COOLDOWN_SECONDS,
            }

        # 5. Generate and store OTP (HMAC keyed with purpose domain separation)
        otp = generate_otp()
        otp_h = hash_otp(otp, purpose="register")

        await store_service.set_otp(email_hash, otp_h, purpose="register", ttl=OTP_TTL_SECONDS)
        await store_service.set_cooldown(email_hash, purpose="register", ttl=OTP_COOLDOWN_SECONDS)

        # 6. Deliver OTP via email
        delivered = await send_otp_email(norm_email, otp, subject_prefix="Registration Code")
        if not delivered:
            await store_service.clear_otp(email_hash, purpose="register")
            await store_service.set_cooldown(
                email_hash, purpose="register", ttl=OTP_COOLDOWN_SECONDS
            )
            logger.warning("Registration OTP delivery failed.")
            return {
                "message": GENERIC_OTP_SENT_MESSAGE,
                "cooldown_seconds": OTP_COOLDOWN_SECONDS,
            }

        return {
            "message": GENERIC_OTP_SENT_MESSAGE,
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

        email_hash = create_email_hash(norm_email)
        otp_h = hash_otp(payload.otp.strip(), purpose="register")

        valid = await store_service.verify_otp(email_hash, otp_h, purpose="register")
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
            has_profile = False
        else:
            if user.password_hash:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account already registered. Please sign in.",
                )
            has_profile = bool(user.profile is not None)
            user.password_hash = pwd_hash
            user.email_hash = email_hash
            user.nickname = chosen_nickname
            user.avatar = avatar
            user.last_login_at = func.now()

        await db.commit()
        await db.refresh(user)

        token = await AuthService._issue_session_token(user.id)
        return token, user, has_profile

    @staticmethod
    async def login(payload: LoginIn, db: AsyncSession) -> tuple[str, User, bool]:
        norm_email = normalize_email(payload.email)
        email_hash = create_email_hash(norm_email)
        login_limit_key = f"login:email:{email_hash}"

        if not await store_service.check_rate_limit(
            login_limit_key,
            settings.login_rate_limit_email_attempts,
            settings.login_rate_limit_email_window_seconds,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many sign-in attempts. Please try again later.",
            )

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

        has_profile = bool(user.profile is not None)
        user.last_login_at = func.now()
        await db.commit()
        await store_service.clear_rate_limit(login_limit_key)

        token = await AuthService._issue_session_token(user.id)
        return token, user, has_profile

    @staticmethod
    async def request_reset_otp(email: str, client_ip: str, db: AsyncSession) -> dict[str, Any]:
        norm_email = normalize_email(email)
        if not is_valid_hust_email(norm_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only HUST student emails (@sis.hust.edu.vn) are supported.",
            )

        # 1. IP Rate limit check
        if not await store_service.check_rate_limit(
            f"ip:{client_ip}",
            settings.rate_limit_ip_requests,
            settings.rate_limit_ip_window_seconds,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests from this IP address. Please try again later.",
            )

        email_hash = create_email_hash(norm_email)

        # 2. Email Rate limit check
        if not await store_service.check_rate_limit(
            f"email:{email_hash}",
            settings.rate_limit_email_requests,
            settings.rate_limit_email_window_seconds,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests for this email address. Please try again later.",
            )

        # 3. Cooldown check
        if await store_service.is_in_cooldown(email_hash, purpose="reset"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {OTP_COOLDOWN_SECONDS} seconds before requesting a new code.",
            )

        stmt = select(User).where(User.email == norm_email)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()

        if not user or not user.password_hash:
            # Prevent account enumeration: return generic message without sending email
            await store_service.set_cooldown(email_hash, purpose="reset", ttl=OTP_COOLDOWN_SECONDS)
            return {
                "message": GENERIC_OTP_SENT_MESSAGE,
                "cooldown_seconds": OTP_COOLDOWN_SECONDS,
            }

        otp = generate_otp()
        otp_h = hash_otp(otp, purpose="reset")

        await store_service.set_otp(email_hash, otp_h, purpose="reset", ttl=OTP_TTL_SECONDS)
        await store_service.set_cooldown(email_hash, purpose="reset", ttl=OTP_COOLDOWN_SECONDS)

        delivered = await send_otp_email(norm_email, otp, subject_prefix="Password Reset Code")
        if not delivered:
            await store_service.clear_otp(email_hash, purpose="reset")
            await store_service.set_cooldown(
                email_hash, purpose="reset", ttl=OTP_COOLDOWN_SECONDS
            )
            logger.warning("Password-reset OTP delivery failed.")
            return {
                "message": GENERIC_OTP_SENT_MESSAGE,
                "cooldown_seconds": OTP_COOLDOWN_SECONDS,
            }

        return {
            "message": GENERIC_OTP_SENT_MESSAGE,
            "cooldown_seconds": OTP_COOLDOWN_SECONDS,
        }

    @staticmethod
    async def reset_password(
        payload: ResetPasswordIn, db: AsyncSession
    ) -> tuple[str, User, bool]:
        norm_email = normalize_email(payload.email)
        email_hash = create_email_hash(norm_email)
        otp_h = hash_otp(payload.otp.strip(), purpose="reset")

        valid = await store_service.verify_otp(email_hash, otp_h, purpose="reset")
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code.",
            )

        has_profile = bool(user.profile is not None)
        user.password_hash = hash_password(payload.new_password)
        user.last_login_at = func.now()
        await db.commit()

        # Revoke all existing sessions across devices before issuing new token
        await store_service.revoke_user_sessions(user.id)

        token = await AuthService._issue_session_token(user.id)
        return token, user, has_profile
