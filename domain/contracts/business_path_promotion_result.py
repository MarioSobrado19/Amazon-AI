from dataclasses import dataclass
from datetime import datetime

from domain.contracts.candidate_business_path import CandidateBusinessPath
from domain.entities._marketplace_validation import aware_datetime, required_text, text_tuple
from domain.entities.business_path import BusinessPath
from domain.enums import PathPromotionAction
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class BusinessPathPromotionResult:
    business_path: BusinessPath
    source_candidate: CandidateBusinessPath
    action: PathPromotionAction
    actor_id: str
    promoted_at: datetime
    version: str
    warnings: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.business_path, BusinessPath):
            raise DomainValidationError("business_path debe ser válido.")
        if not isinstance(self.source_candidate, CandidateBusinessPath):
            raise DomainValidationError("source_candidate debe ser válido.")
        if self.business_path.source_candidate_id != self.source_candidate.candidate_path_id:
            raise DomainValidationError("business_path no corresponde al candidato de origen.")
        if not isinstance(self.action, PathPromotionAction):
            raise DomainValidationError("action debe ser explícita y válida.")
        object.__setattr__(self, "actor_id", required_text(self.actor_id, "actor_id"))
        object.__setattr__(self, "promoted_at", aware_datetime(self.promoted_at, "promoted_at"))
        object.__setattr__(self, "version", required_text(self.version, "version"))
        object.__setattr__(self, "warnings", text_tuple(self.warnings, "warnings"))

    def to_dict(self):
        return {
            "business_path": self.business_path.to_dict(),
            "source_candidate": self.source_candidate.to_dict(),
            "action": self.action.value,
            "actor_id": self.actor_id,
            "promoted_at": self.promoted_at.isoformat(),
            "version": self.version,
            "warnings": list(self.warnings),
        }
