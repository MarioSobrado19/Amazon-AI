from dataclasses import dataclass

from domain.entities._validation import required_text
from domain.entities.result import Result
from domain.enums import ConfidenceLevel, DecisionState, RiskLevel
from domain.exceptions import DomainValidationError


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
        }

