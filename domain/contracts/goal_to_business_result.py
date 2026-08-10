from dataclasses import dataclass
from datetime import datetime

from domain.contracts.candidate_business_path import CandidateBusinessPath
from domain.entities._marketplace_validation import aware_datetime, required_text, text_tuple
from domain.enums import CandidatePathState
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class GoalToBusinessResult:
    candidate_paths: tuple[CandidateBusinessPath, ...]
    invalidated_paths: tuple[CandidateBusinessPath, ...]
    global_missing_data: tuple[str, ...]
    warnings: tuple[str, ...]
    continuation_questions: tuple[str, ...]
    version: str
    generated_at: datetime

    def __post_init__(self):
        for field in ("candidate_paths", "invalidated_paths"):
            values = tuple(getattr(self, field))
            if any(not isinstance(x, CandidateBusinessPath) for x in values): raise DomainValidationError(f"{field} contiene caminos inválidos.")
            object.__setattr__(self, field, values)
        if any(x.state is CandidatePathState.INVALIDATED for x in self.candidate_paths): raise DomainValidationError("candidate_paths no admite invalidados.")
        if any(x.state is not CandidatePathState.INVALIDATED for x in self.invalidated_paths): raise DomainValidationError("invalidated_paths solo admite invalidados.")
        for field in ("global_missing_data", "warnings", "continuation_questions"):
            object.__setattr__(self, field, text_tuple(getattr(self, field), field))
        object.__setattr__(self, "version", required_text(self.version, "version"))
        object.__setattr__(self, "generated_at", aware_datetime(self.generated_at, "generated_at"))

    def to_dict(self):
        return {"candidate_paths": [x.to_dict() for x in self.candidate_paths], "invalidated_paths": [x.to_dict() for x in self.invalidated_paths],
                "global_missing_data": list(self.global_missing_data), "warnings": list(self.warnings),
                "continuation_questions": list(self.continuation_questions), "version": self.version, "generated_at": self.generated_at.isoformat()}
