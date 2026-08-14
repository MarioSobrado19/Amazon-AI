from enum import Enum


class ResearchQuestionStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    VERIFIED = "verified"
    STALE = "stale"
