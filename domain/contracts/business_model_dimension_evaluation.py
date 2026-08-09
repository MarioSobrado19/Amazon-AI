from dataclasses import dataclass

from domain.entities._marketplace_validation import required_text, text_tuple
from domain.enums import ConfidenceLevel
from domain.exceptions import DomainValidationError


DIMENSION_EVALUATIONS = {
    "favorable",
    "neutral",
    "desfavorable",
    "incompatible",
    "desconocida",
}


@dataclass(frozen=True, slots=True)
class BusinessModelDimensionEvaluation:
    """Conclusión explicable de una dimensión; nunca es un puntaje."""

    dimension: str
    evaluation: str
    explanation: str
    confidence: ConfidenceLevel
    evidence: tuple[str, ...] = ()
    missing_data: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "dimension", required_text(self.dimension, "dimension"))
        evaluation = required_text(self.evaluation, "evaluation")
        if evaluation not in DIMENSION_EVALUATIONS:
            raise DomainValidationError("evaluation no es válida.")
        object.__setattr__(self, "evaluation", evaluation)
        object.__setattr__(
            self, "explanation", required_text(self.explanation, "explanation")
        )
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser válido.")
        object.__setattr__(self, "evidence", text_tuple(self.evidence, "evidence"))
        object.__setattr__(
            self, "missing_data", text_tuple(self.missing_data, "missing_data")
        )

    def to_dict(self):
        return {
            "dimension": self.dimension,
            "evaluation": self.evaluation,
            "explanation": self.explanation,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
            "missing_data": list(self.missing_data),
        }
