from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from domain.entities._validation import required_text
from domain.enums import InformationSource, RiskLevel
from domain.exceptions import DomainValidationError
from domain.value_objects._goal_context_validation import (
    aware_datetime,
    declared_source,
    optional_scalar,
    serialize_scalar,
)


@dataclass(frozen=True, slots=True)
class ConstraintDeclaration:
    """Límite declarado que puede impedir o condicionar una alternativa."""

    constraint_type: str
    explanation: str
    declared_at: datetime
    value: str | bool | Decimal | None = None
    severity: RiskLevel | None = None
    source: InformationSource = InformationSource.USER_DECLARED

    def __post_init__(self):
        object.__setattr__(
            self,
            "constraint_type",
            required_text(self.constraint_type, "constraint_type"),
        )
        object.__setattr__(
            self, "explanation", required_text(self.explanation, "explanation")
        )
        object.__setattr__(self, "value", optional_scalar(self.value, "value"))
        if self.severity is not None and not isinstance(self.severity, RiskLevel):
            raise DomainValidationError("severity debe ser un nivel válido.")
        declared_source(self.source)
        object.__setattr__(
            self, "declared_at", aware_datetime(self.declared_at, "declared_at")
        )

    def to_dict(self):
        return {
            "constraint_type": self.constraint_type,
            "value": serialize_scalar(self.value),
            "severity": self.severity.value if self.severity else None,
            "explanation": self.explanation,
            "source": self.source.value,
            "declared_at": self.declared_at.isoformat(),
        }
