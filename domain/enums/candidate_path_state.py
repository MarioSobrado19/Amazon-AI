from enum import Enum


class CandidatePathState(str, Enum):
    HYPOTHESIS = "hypothesis"
    INCOMPLETE = "incomplete"
    RESEARCHABLE = "researchable"
    INVALIDATED = "invalidated"
