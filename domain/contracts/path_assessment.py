from dataclasses import dataclass

from domain.entities._marketplace_validation import required_text, text_tuple
from domain.enums import ConfidenceLevel
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class PathDimensionAssessment:
    dimension: str
    evaluation: str
    explanation: str
    confidence: ConfidenceLevel
    evidence: tuple[str, ...] = ()
    missing_data: tuple[str, ...] = ()
    relevant_constraints: tuple[str, ...] = ()

    def __post_init__(self):
        for field in ("dimension", "evaluation", "explanation"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser válido.")
        for field in ("evidence", "missing_data", "relevant_constraints"):
            object.__setattr__(self, field, text_tuple(getattr(self, field), field))

    def to_dict(self):
        return {"dimension": self.dimension, "evaluation": self.evaluation,
                "explanation": self.explanation, "confidence": self.confidence.value,
                "evidence": list(self.evidence), "missing_data": list(self.missing_data),
                "relevant_constraints": list(self.relevant_constraints)}


@dataclass(frozen=True, slots=True)
class PathAssessment:
    dimensions: tuple[PathDimensionAssessment, ...]
    confidence: ConfidenceLevel
    version: str

    def __post_init__(self):
        values = tuple(self.dimensions)
        if any(not isinstance(item, PathDimensionAssessment) for item in values):
            raise DomainValidationError("dimensions contiene valores inválidos.")
        object.__setattr__(self, "dimensions", values)
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser válido.")
        object.__setattr__(self, "version", required_text(self.version, "version"))

    def to_dict(self):
        return {"dimensions": [item.to_dict() for item in self.dimensions],
                "confidence": self.confidence.value, "version": self.version}
