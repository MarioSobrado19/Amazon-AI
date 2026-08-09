from dataclasses import dataclass
from datetime import datetime

from domain.contracts.business_model_assessment import BusinessModelAssessment
from domain.entities import BusinessModel
from domain.entities._identity import internal_id
from domain.entities._marketplace_validation import aware_datetime, optional_text, required_text, text_tuple
from domain.enums import ConfidenceLevel
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class BusinessModelComparisonResult:
    """Comparación multidimensional; no contiene ni deriva un score único."""

    comparison_id: str
    version: str
    assessed_at: datetime
    assessments: tuple[BusinessModelAssessment, ...]
    confidence: ConfidenceLevel
    compatible_models: tuple[BusinessModel, ...] = ()
    incompatible_models: tuple[BusinessModel, ...] = ()
    consideration_model: BusinessModel | None = None
    consideration_reason: str | None = None
    alternatives: tuple[BusinessModel, ...] = ()
    missing_data: tuple[str, ...] = ()
    continuation_question: str = "¿Qué información deseas completar para comparar mejor?"
    simplified_for_beginner: bool = False

    def __post_init__(self):
        object.__setattr__(
            self, "comparison_id", internal_id(self.comparison_id, "comparison_id")
        )
        object.__setattr__(self, "version", required_text(self.version, "version"))
        object.__setattr__(
            self, "assessed_at", aware_datetime(self.assessed_at, "assessed_at")
        )
        assessments = tuple(self.assessments)
        if any(not isinstance(item, BusinessModelAssessment) for item in assessments):
            raise DomainValidationError("assessments contiene valores inválidos.")
        object.__setattr__(self, "assessments", assessments)
        for field_name in ("compatible_models", "incompatible_models", "alternatives"):
            values = tuple(getattr(self, field_name))
            if any(not isinstance(item, BusinessModel) for item in values):
                raise DomainValidationError(f"{field_name} contiene modelos inválidos.")
            object.__setattr__(self, field_name, values)
        if self.consideration_model is not None and not isinstance(
            self.consideration_model, BusinessModel
        ):
            raise DomainValidationError("consideration_model debe ser BusinessModel.")
        object.__setattr__(
            self,
            "consideration_reason",
            optional_text(self.consideration_reason, "consideration_reason"),
        )
        object.__setattr__(self, "missing_data", text_tuple(self.missing_data, "missing_data"))
        object.__setattr__(
            self,
            "continuation_question",
            required_text(self.continuation_question, "continuation_question"),
        )
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser válido.")
        if not isinstance(self.simplified_for_beginner, bool):
            raise DomainValidationError("simplified_for_beginner debe ser booleano.")

    def to_dict(self):
        return {
            "comparison_id": self.comparison_id,
            "version": self.version,
            "assessed_at": self.assessed_at.isoformat(),
            "assessments": [item.to_dict() for item in self.assessments],
            "confidence": self.confidence.value,
            "compatible_models": [item.to_dict() for item in self.compatible_models],
            "incompatible_models": [item.to_dict() for item in self.incompatible_models],
            "consideration_model": (
                self.consideration_model.to_dict() if self.consideration_model else None
            ),
            "consideration_reason": self.consideration_reason,
            "alternatives": [item.to_dict() for item in self.alternatives],
            "missing_data": list(self.missing_data),
            "continuation_question": self.continuation_question,
            "simplified_for_beginner": self.simplified_for_beginner,
        }
