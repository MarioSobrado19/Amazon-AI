from enum import Enum


class BusinessPathState(str, Enum):
    SAVED = "saved"
    INVESTIGATING = "investigating"
    PAUSED = "paused"
    INVALIDATED = "invalidated"
    CLOSED = "closed"
