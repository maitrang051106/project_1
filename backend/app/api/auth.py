import logging
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginIn,
    RegisterIn,
    RequestOtpIn,
    ResetPasswordIn,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_expire_seconds,
        path="/",
    )


def _serialize_user_response(user: User, token: str, has_profile: bool) -> dict[str, Any]:
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


@router.post("/request-register-otp")
async def request_register_otp(
    payload: RequestOtpIn, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    return await AuthService.request_register_otp(payload.email, db)


@router.post("/register")
async def register(
    payload: RegisterIn, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    token, user, has_profile = await AuthService.register(payload, db)
    _set_auth_cookie(response, token)
    return _serialize_user_response(user, token, has_profile)


@router.post("/login")
async def login(
    payload: LoginIn, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    token, user, has_profile = await AuthService.login(payload, db)
    _set_auth_cookie(response, token)
    return _serialize_user_response(user, token, has_profile)


@router.post("/request-reset-otp")
async def request_reset_otp(
    payload: RequestOtpIn, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    return await AuthService.request_reset_otp(payload.email, db)


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordIn, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    token, user, has_profile = await AuthService.reset_password(payload, db)
    _set_auth_cookie(response, token)
    return {
        "message": "Password reset successfully.",
        **_serialize_user_response(user, token, has_profile),
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
