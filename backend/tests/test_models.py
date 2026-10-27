from sqlalchemy import CHAR
from sqlalchemy.orm import configure_mappers

from app.models import Base, Conversation, Profile, User
from app.models.enums import ConversationType, Gender, UserRole, UserStatus


def test_schema_contains_only_mvp_tables() -> None:
    assert set(Base.metadata.tables) == {"users", "profiles", "conversations"}


def test_user_schema_and_enum_values() -> None:
    users = User.__table__

    assert users.c.email_hash.type.length == 64
    assert isinstance(users.c.email_hash.type, CHAR)
    assert users.c.anon_name.type.length == 50
    assert users.c.email_hash.nullable is False
    assert {constraint.name for constraint in users.constraints} >= {
        "uq_users_email_hash"
    }
    assert users.c.status.type.enums == ["active", "banned"]
    assert users.c.role.type.enums == ["user", "admin"]
    assert [status.value for status in UserStatus] == [
        "active",
        "banned",
    ]
    assert [role.value for role in UserRole] == ["user", "admin"]


def test_profile_schema_fields() -> None:
    profiles = Profile.__table__

    assert profiles.c.user_id.primary_key is True
    assert profiles.c.gender.nullable is False
    assert profiles.c.gender.type.length == 10
    assert profiles.c.faculty_code.nullable is False
    assert profiles.c.faculty_code.type.length == 20
    assert profiles.c.major_code.nullable is False
    assert profiles.c.major_code.type.length == 20
    assert profiles.c.cohort.nullable is False
    user_foreign_key = next(iter(profiles.c.user_id.foreign_keys))
    assert user_foreign_key.ondelete == "CASCADE"


def test_conversation_schema_and_relationships() -> None:
    conversations = Conversation.__table__
    configure_mappers()

    assert conversations.c.type.name == "type"
    assert conversations.c.score.nullable is True
    assert {index.name for index in conversations.indexes} == {
        "ix_conversations_user_a",
        "ix_conversations_user_b",
    }
    assert any(
        constraint.name == "ck_conversations_distinct_users"
        for constraint in conversations.constraints
    )
    assert ConversationType.HUMAN.value == "human"
    assert ConversationType.BOT.value == "bot"
