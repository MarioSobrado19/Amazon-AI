from dataclasses import dataclass
from decimal import Decimal

from domain.entities._validation import optional_text, required_text
from domain.enums import ConfidenceLevel, InformationSource
from domain.exceptions import DomainValidationError
from domain.value_objects._goal_context_validation import (
    declared_source,
    optional_non_negative_decimal,
)


@dataclass(frozen=True, slots=True)
class ResourceAvailability:
    """Recurso declarado, sin inferir disponibilidad o capacidad ausente."""

    resource_type: str
    available: bool | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    source: InformationSource = InformationSource.USER_DECLARED
    confidence: ConfidenceLevel | None = None

    def __post_init__(self):
        object.__setattr__(
            self,
            "resource_type",
            required_text(self.resource_type, "resource_type"),
        )
        if self.available is not None and not isinstance(self.available, bool):
            raise DomainValidationError("available debe ser booleano o None.")
        object.__setattr__(
            self,
            "quantity",
            optional_non_negative_decimal(self.quantity, "quantity"),
        )
        object.__setattr__(self, "unit", optional_text(self.unit, "unit"))
        if self.quantity is not None and self.unit is None:
            raise DomainValidationError("unit es obligatorio cuando existe quantity.")
        if self.confidence is not None and not isinstance(
            self.confidence, ConfidenceLevel
        ):
            raise DomainValidationError("confidence debe ser un nivel válido.")
        declared_source(self.source)

    def to_dict(self):
        return {
            "resource_type": self.resource_type,
            "available": self.available,
            "quantity": str(self.quantity) if self.quantity is not None else None,
            "unit": self.unit,
            "source": self.source.value,
            "confidence": self.confidence.value if self.confidence else None,
        }
