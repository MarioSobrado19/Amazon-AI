from enum import Enum


class InvestigationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PARTIAL = "partial"
    VERIFIED = "verified"
    STALE = "stale"
    DISCARDED = "discarded"
