from dataclasses import dataclass

from domain.contracts.path_assessment import PathAssessment
from domain.entities import (
    BusinessModel,
    Marketplace,
    MarketplaceConditionSnapshot,
    OpportunityScenario,
    Result,
)
from domain.entities._marketplace_validation import required_text, text_tuple
from domain.enums import CandidatePathState, ConfidenceLevel
from domain.exceptions import DomainValidationError
from domain.value_objects import GoalContextSnapshot


@dataclass(frozen=True, slots=True)
class CandidateBusinessPath:
    """Hipótesis temporal, sin persistencia, historial ni decisión humana."""
    candidate_path_id: str
    objective_id: str
    context: GoalContextSnapshot
    assessment: PathAssessment
    state: CandidatePathState
    confidence: ConfidenceLevel
    version: str
    marketplace: Marketplace | None = None
    business_model: BusinessModel | None = None
    scenario: OpportunityScenario | None = None
    required_resources: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    relevant_constraints: tuple[str, ...] = ()
    related_preferences: tuple[str, ...] = ()
    available_evidence: tuple[Result, ...] = ()
    condition_snapshots: tuple[MarketplaceConditionSnapshot, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    assumptions: tuple[Result, ...] = ()
    risks: tuple[str, ...] = ()
    invalidators: tuple[str, ...] = ()
    next_steps: tuple[str, ...] = ()
    appearance_reason: str = "Candidato suministrado para evaluación."

    def __post_init__(self):
        for field in ("candidate_path_id", "objective_id", "version", "appearance_reason"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if not isinstance(self.context, GoalContextSnapshot) or self.context.objective_id != self.objective_id:
            raise DomainValidationError("context debe pertenecer al objetivo del camino.")
        if not isinstance(self.assessment, PathAssessment):
            raise DomainValidationError("assessment debe ser PathAssessment.")
        if not isinstance(self.state, CandidatePathState) or not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("state y confidence deben ser válidos.")
        for field, kind in (("marketplace", Marketplace), ("business_model", BusinessModel), ("scenario", OpportunityScenario)):
            value = getattr(self, field)
            if value is not None and not isinstance(value, kind):
                raise DomainValidationError(f"{field} no es válido.")
        for field in ("required_resources", "required_capabilities", "relevant_constraints", "related_preferences", "missing_evidence", "risks", "invalidators", "next_steps"):
            object.__setattr__(self, field, text_tuple(getattr(self, field), field))
        for field in ("available_evidence", "assumptions"):
            values = tuple(getattr(self, field))
            if any(not isinstance(item, Result) for item in values):
                raise DomainValidationError(f"{field} contiene evidencia inválida.")
            object.__setattr__(self, field, values)
        snapshots = tuple(self.condition_snapshots)
        if any(not isinstance(item, MarketplaceConditionSnapshot) for item in snapshots):
            raise DomainValidationError("condition_snapshots contiene valores inválidos.")
        object.__setattr__(self, "condition_snapshots", snapshots)

    def to_dict(self):
        return {"candidate_path_id": self.candidate_path_id, "objective_id": self.objective_id,
                "context": self.context.to_dict(), "marketplace": self.marketplace.to_dict() if self.marketplace else None,
                "business_model": self.business_model.to_dict() if self.business_model else None,
                "scenario": self.scenario.to_dict() if self.scenario else None,
                "assessment": self.assessment.to_dict(), "state": self.state.value,
                "confidence": self.confidence.value, "version": self.version,
                "required_resources": list(self.required_resources), "required_capabilities": list(self.required_capabilities),
                "relevant_constraints": list(self.relevant_constraints), "related_preferences": list(self.related_preferences),
                "available_evidence": [x.to_dict() for x in self.available_evidence], "missing_evidence": list(self.missing_evidence),
                "condition_snapshots": [x.to_dict() for x in self.condition_snapshots],
                "assumptions": [x.to_dict() for x in self.assumptions], "risks": list(self.risks),
                "invalidators": list(self.invalidators),
                "next_steps": list(self.next_steps), "appearance_reason": self.appearance_reason}
