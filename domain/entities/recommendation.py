from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite

from domain.entities._validation import required_text
from domain.entities.result import Result
from domain.enums import ConfidenceLevel, DecisionState, RiskLevel
from domain.exceptions import DomainValidationError


def _immutable_context_value(value):
    if value is None or isinstance(value, (str, int)):
        return not isinstance(value, bool)
    if isinstance(value, float):
        return isfinite(value)
    if isinstance(value, tuple):
        return all(_immutable_context_value(item) for item in value)
    return False


@dataclass(frozen=True, slots=True, eq=False)
class Recommendation:
    """Orientación explicable que permanece separada de la decisión humana."""

    recommendation_id: str
    state: DecisionState
    message: str
    explanation: str
    confidence: ConfidenceLevel
    evidence: tuple[Result, ...] = ()
    risks: tuple[tuple[RiskLevel, str], ...] = ()
    limitations: tuple[str, ...] = ()
    opportunity_id: str | None = None
    favorable_evidence: tuple[str, ...] = ()
    missing_data: tuple[str, ...] = ()
    next_step: str | None = None
    alternatives: tuple[str, ...] = ()
    conditions_to_advance: tuple[str, ...] = ()
    applied_rules: tuple[str, ...] = ()
    continuation_question: str | None = None
    context_used: tuple[tuple[str, object], ...] = ()
    version: str = "1"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        object.__setattr__(
            self,
            "recommendation_id",
            required_text(self.recommendation_id, "recommendation_id"),
        )
        if not isinstance(self.state, DecisionState):
            raise DomainValidationError("state debe ser un DecisionState válido.")
        object.__setattr__(self, "message", required_text(self.message, "message"))
        object.__setattr__(
            self,
            "explanation",
            required_text(self.explanation, "explanation"),
        )
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser un nivel válido.")

        evidence = tuple(self.evidence)
        if any(not isinstance(item, Result) for item in evidence):
            raise DomainValidationError("evidence debe contener Result válidos.")
        object.__setattr__(self, "evidence", evidence)

        risks = tuple(self.risks)
        normalized_risks = []
        for risk in risks:
            if not isinstance(risk, tuple) or len(risk) != 2:
                raise DomainValidationError("risks debe contener nivel y explicación.")
            level, explanation = risk
            if not isinstance(level, RiskLevel):
                raise DomainValidationError("risk level debe ser válido.")
            normalized_risks.append(
                (level, required_text(explanation, "risk explanation"))
            )
        object.__setattr__(self, "risks", tuple(normalized_risks))

        limitations = tuple(
            required_text(item, "limitation") for item in self.limitations
        )
        object.__setattr__(self, "limitations", limitations)
        if self.opportunity_id is not None:
            object.__setattr__(
                self,
                "opportunity_id",
                required_text(self.opportunity_id, "opportunity_id"),
            )
        for field_name in (
            "favorable_evidence",
            "missing_data",
            "alternatives",
            "conditions_to_advance",
            "applied_rules",
        ):
            values = tuple(
                required_text(item, field_name) for item in getattr(self, field_name)
            )
            object.__setattr__(self, field_name, values)
        if self.next_step is not None:
            object.__setattr__(
                self, "next_step", required_text(self.next_step, "next_step")
            )
        if self.continuation_question is not None:
            object.__setattr__(
                self,
                "continuation_question",
                required_text(self.continuation_question, "continuation_question"),
            )
        context = tuple(self.context_used)
        if any(not isinstance(item, tuple) or len(item) != 2 for item in context):
            raise DomainValidationError("context_used debe contener pares clave y valor.")
        if any(
            not isinstance(key, str) or not _immutable_context_value(value)
            for key, value in context
        ):
            raise DomainValidationError(
                "context_used debe contener valores inmutables y serializables."
            )
        object.__setattr__(self, "context_used", context)
        object.__setattr__(self, "version", required_text(self.version, "version"))
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise DomainValidationError("created_at debe incluir zona horaria.")

    def __eq__(self, other):
        if not isinstance(other, Recommendation):
            return NotImplemented
        return self.recommendation_id == other.recommendation_id

    def __hash__(self):
        return hash(self.recommendation_id)

    def to_dict(self):
        return {
            "recommendation_id": self.recommendation_id,
            "state": self.state.value,
            "message": self.message,
            "explanation": self.explanation,
            "confidence": self.confidence.value,
            "evidence": [item.to_dict() for item in self.evidence],
            "risks": [
                {"level": level.value, "explanation": explanation}
                for level, explanation in self.risks
            ],
            "limitations": list(self.limitations),
            "opportunity_id": self.opportunity_id,
            "favorable_evidence": list(self.favorable_evidence),
            "missing_data": list(self.missing_data),
            "next_step": self.next_step,
            "alternatives": list(self.alternatives),
            "conditions_to_advance": list(self.conditions_to_advance),
            "applied_rules": list(self.applied_rules),
            "continuation_question": self.continuation_question,
            "context_used": dict(self.context_used),
            "version": self.version,
            "created_at": self.created_at.isoformat(),
        }
