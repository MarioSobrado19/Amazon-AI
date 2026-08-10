from dataclasses import dataclass

from domain.entities._validation import optional_text, required_text
from domain.enums import ConfidenceLevel, InformationSource
from domain.exceptions import DomainValidationError
from domain.value_objects._goal_context_validation import declared_source


@dataclass(frozen=True, slots=True)
class CapabilityDeclaration:
    """Capacidad declarada explícitamente; nunca inferida de otros datos."""

    capability_type: str
    available: bool | None = None
    level: str | None = None
    explanation: str | None = None
    source: InformationSource = InformationSource.USER_DECLARED
    confidence: ConfidenceLevel | None = None

    def __post_init__(self):
        object.__setattr__(
            self,
            "capability_type",
            required_text(self.capability_type, "capability_type"),
        )
        if self.available is not None and not isinstance(self.available, bool):
            raise DomainValidationError("available debe ser booleano o None.")
        object.__setattr__(self, "level", optional_text(self.level, "level"))
        object.__setattr__(
            self, "explanation", optional_text(self.explanation, "explanation")
        )
        if self.confidence is not None and not isinstance(
            self.confidence, ConfidenceLevel
        ):
            raise DomainValidationError("confidence debe ser un nivel válido.")
        declared_source(self.source)

    def to_dict(self):
        return {
            "capability_type": self.capability_type,
            "available": self.available,
            "level": self.level,
            "explanation": self.explanation,
            "source": self.source.value,
            "confidence": self.confidence.value if self.confidence else None,
        }
