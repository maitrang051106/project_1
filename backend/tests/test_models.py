from sqlalchemy import Enum as SaEnum
from sqlalchemy.dialects import mysql

from app.models import (
    Base,
    Conversation,
    ConversationType,
    DirectMessage,
    Friendship,
    Gender,
    Profile,
    TargetCohort,
    TargetGender,
    TargetMajorFaculty,
    User,
    UserRole,
    UserStatus,
)


def test_schema_contains_mvp_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "profiles",
        "conversations",
        "friendships",
        "direct_messages",
    }


def test_user_schema_and_enum_values() -> None:
    user_columns = Base.metadata.tables["users"].columns

    assert "email" in user_columns
    assert "password_hash" in user_columns
    assert "avatar" in user_columns
    assert "email_hash" in user_columns
    assert "nickname" in user_columns
    assert "trust_score" in user_columns
    assert "status" in user_columns
    assert "role" in user_columns

    status_type = user_columns["status"].type
    assert isinstance(status_type, (SaEnum, mysql.ENUM))
    assert status_type.enums == ["active", "banned"]
    assert UserStatus.ACTIVE.value == "active"
    assert UserStatus.BANNED.value == "banned"
    assert UserRole.USER.value == "user"
    assert UserRole.ADMIN.value == "admin"


def test_profile_schema_fields() -> None:
    profile_columns = Base.metadata.tables["profiles"].columns

    assert "gender" in profile_columns
    assert "faculty_code" in profile_columns
    assert "major_code" in profile_columns
    assert "cohort" in profile_columns

    assert Gender.MALE.value == "male"
    assert Gender.FEMALE.value == "female"
    assert TargetGender.ANY.value == "any"
    assert TargetMajorFaculty.SAME_MAJOR.value == "same_major"
    assert TargetCohort.SENIOR.value == "senior"


def test_conversation_schema_and_relationships() -> None:
    conv_columns = Base.metadata.tables["conversations"].columns
    assert "type" in conv_columns
    assert conv_columns["type"].type.enums == ["human", "bot"]
    assert ConversationType.HUMAN.value == "human"
    assert ConversationType.BOT.value == "bot"
