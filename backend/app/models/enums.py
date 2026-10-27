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
    NAM = "nam"
    NU = "nu"


class TargetGender(str, Enum):
    NAM = "nam"
    NU = "nu"
    BAT_KI = "bat_ki"


class TargetMajorFaculty(str, Enum):
    CUNG_NGANH = "cung_nganh"
    CUNG_TRUONG_KHAC_NGANH = "cung_truong_khac_nganh"
    KHAC_TRUONG = "khac_truong"
    BAT_KI = "bat_ki"


class TargetCohort(str, Enum):
    KHOA_TREN = "khoa_tren"
    KHOA_DUOI = "khoa_duoi"
    CUNG_KHOA = "cung_khoa"
    BAT_KI = "bat_ki"
