from dataclasses import dataclass
from datetime import datetime

from domain.contracts.business_model_dimension_evaluation import (
    BusinessModelDimensionEvaluation,
)
from domain.entities import BusinessModel, OpportunityScenario, Result
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
    scenario: OpportunityScenario | None
    compatibility: str
    confidence: ConfidenceLevel
    version: str
    assessed_at: datetime
    favorable_factors: tuple[str, ...] = ()
    unfavorable_factors: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    rules_applied: tuple[str, ...] = ()
    evidence: tuple[Result, ...] = ()
    business_model: BusinessModel | None = None
    dimensions: tuple[BusinessModelDimensionEvaluation, ...] = ()
    risks: tuple[str, ...] = ()
    requirements: tuple[str, ...] = ()
    seller_responsibilities: tuple[str, ...] = ()
    marketplace_responsibilities: tuple[str, ...] = ()
    favorable_context: tuple[str, ...] = ()
    unfavorable_context: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    change_conditions: tuple[str, ...] = ()
    educational_topics: tuple[str, ...] = ()
    simplified_for_beginner: bool = False

    def __post_init__(self):
        object.__setattr__(
            self, "assessment_id", required_text(self.assessment_id, "assessment_id")
        )
        if self.scenario is not None and not isinstance(self.scenario, OpportunityScenario):
            raise DomainValidationError("scenario debe ser OpportunityScenario válido.")
        business_model = self.business_model
        if business_model is None and self.scenario is not None:
            business_model = self.scenario.business_model
        if not isinstance(business_model, BusinessModel):
            raise DomainValidationError("business_model es obligatorio.")
        if (
            self.scenario is not None
            and self.scenario.business_model.business_model_id
            != business_model.business_model_id
        ):
            raise DomainValidationError("scenario y business_model no coinciden.")
        object.__setattr__(self, "business_model", business_model)
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
            "risks",
            "requirements",
            "seller_responsibilities",
            "marketplace_responsibilities",
            "favorable_context",
            "unfavorable_context",
            "reasons",
            "change_conditions",
            "educational_topics",
        ):
            object.__setattr__(self, field_name, text_tuple(getattr(self, field_name), field_name))
        evidence = tuple(self.evidence)
        if any(not isinstance(item, Result) for item in evidence):
            raise DomainValidationError("evidence debe contener Result válidos.")
        object.__setattr__(self, "evidence", evidence)
        dimensions = tuple(self.dimensions)
        if any(not isinstance(item, BusinessModelDimensionEvaluation) for item in dimensions):
            raise DomainValidationError(
                "dimensions debe contener BusinessModelDimensionEvaluation válidas."
            )
        object.__setattr__(self, "dimensions", dimensions)
        if not isinstance(self.simplified_for_beginner, bool):
            raise DomainValidationError("simplified_for_beginner debe ser booleano.")

    def to_dict(self):
        return {
            "assessment_id": self.assessment_id,
            "scenario": self.scenario.to_dict() if self.scenario else None,
            "business_model": self.business_model.to_dict(),
            "compatibility": self.compatibility,
            "confidence": self.confidence.value,
            "version": self.version,
            "assessed_at": self.assessed_at.isoformat(),
            "favorable_factors": list(self.favorable_factors),
            "unfavorable_factors": list(self.unfavorable_factors),
            "missing_information": list(self.missing_information),
            "rules_applied": list(self.rules_applied),
            "evidence": [item.to_dict() for item in self.evidence],
            "dimensions": [item.to_dict() for item in self.dimensions],
            "risks": list(self.risks),
            "requirements": list(self.requirements),
            "seller_responsibilities": list(self.seller_responsibilities),
            "marketplace_responsibilities": list(self.marketplace_responsibilities),
            "favorable_context": list(self.favorable_context),
            "unfavorable_context": list(self.unfavorable_context),
            "reasons": list(self.reasons),
            "change_conditions": list(self.change_conditions),
            "educational_topics": list(self.educational_topics),
            "simplified_for_beginner": self.simplified_for_beginner,
        }
