from dataclasses import dataclass
from datetime import datetime

from domain.entities import OpportunityScenario, Result
from domain.entities._marketplace_validation import aware_datetime, required_text, text_tuple
from domain.enums import ConfidenceLevel
from domain.exceptions import DomainValidationError


COMPATIBILITY_STATES = {
    "compatible",
    "compatible_con_condiciones",
    "indeterminado",
    "incompatible",
    "no_disponible",
}


@dataclass(frozen=True, slots=True)
class BusinessModelAssessment:
    """Comparación multidimensional explicable, sin score único."""

    assessment_id: str
    scenario: OpportunityScenario
    compatibility: str
    confidence: ConfidenceLevel
    version: str
    assessed_at: datetime
    favorable_factors: tuple[str, ...] = ()
    unfavorable_factors: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    rules_applied: tuple[str, ...] = ()
    evidence: tuple[Result, ...] = ()

    def __post_init__(self):
        object.__setattr__(
            self, "assessment_id", required_text(self.assessment_id, "assessment_id")
        )
        if not isinstance(self.scenario, OpportunityScenario):
            raise DomainValidationError("scenario debe ser OpportunityScenario válido.")
        compatibility = required_text(self.compatibility, "compatibility")
        if compatibility not in COMPATIBILITY_STATES:
            raise DomainValidationError("compatibility no es válido.")
        object.__setattr__(self, "compatibility", compatibility)
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser válido.")
        object.__setattr__(self, "version", required_text(self.version, "version"))
        object.__setattr__(
            self, "assessed_at", aware_datetime(self.assessed_at, "assessed_at")
        )
        for field_name in (
            "favorable_factors",
            "unfavorable_factors",
            "missing_information",
            "rules_applied",
        ):
            object.__setattr__(self, field_name, text_tuple(getattr(self, field_name), field_name))
        evidence = tuple(self.evidence)
        if any(not isinstance(item, Result) for item in evidence):
            raise DomainValidationError("evidence debe contener Result válidos.")
        object.__setattr__(self, "evidence", evidence)

    def to_dict(self):
        return {
            "assessment_id": self.assessment_id,
            "scenario": self.scenario.to_dict(),
            "compatibility": self.compatibility,
            "confidence": self.confidence.value,
            "version": self.version,
            "assessed_at": self.assessed_at.isoformat(),
            "favorable_factors": list(self.favorable_factors),
            "unfavorable_factors": list(self.unfavorable_factors),
            "missing_information": list(self.missing_information),
            "rules_applied": list(self.rules_applied),
            "evidence": [item.to_dict() for item in self.evidence],
        }

