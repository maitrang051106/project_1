from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "active"
    BANNED = "banned"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class ConversationType(str, Enum):
    HUMAN = "human"
    BOT = "bot"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class TargetGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    ANY = "any"


class TargetMajorFaculty(str, Enum):
    SAME_MAJOR = "same_major"
    SAME_FACULTY = "same_faculty"
    DIFFERENT_FACULTY = "different_faculty"
    ANY = "any"


class TargetCohort(str, Enum):
    SENIOR = "senior"
    JUNIOR = "junior"
    SAME_COHORT = "same_cohort"
    ANY = "any"
