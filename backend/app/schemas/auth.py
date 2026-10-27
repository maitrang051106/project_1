from pydantic import BaseModel, Field


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


class UserOut(BaseModel):
    id: int
    email: str | None = None
    nickname: str
    avatar: str
    trust_score: int
    role: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut
    has_profile: bool
