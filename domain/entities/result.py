from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from math import isfinite

from domain.entities._validation import optional_text, required_text
from domain.enums import ConfidenceLevel, EvidenceType
from domain.exceptions import DomainValidationError
from domain.value_objects import Money, Percentage


def _serialize_value(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    return value


def _immutable_value(value):
    if isinstance(value, float):
        return isfinite(value)
    if isinstance(value, (str, int, bool, Decimal, Money, Percentage)):
        return not isinstance(value, Decimal) or value.is_finite()
    if isinstance(value, tuple):
        return all(_immutable_value(item) for item in value)
    return False


@dataclass(frozen=True, slots=True, eq=False)
class Result:
    """Resultado inmutable que declara si es dato, estimación o supuesto."""

    result_id: str
    name: str
    value: object
    evidence_type: EvidenceType
    source: str
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "result_id", required_text(self.result_id, "result_id"))
        object.__setattr__(self, "name", required_text(self.name, "name"))
        if not _immutable_value(self.value):
            raise DomainValidationError(
                "value debe ser un valor inmutable, finito y serializable."
            )
        if not isinstance(self.evidence_type, EvidenceType):
            raise DomainValidationError(
                "evidence_type debe indicar dato, estimación o supuesto."
            )
        object.__setattr__(self, "source", required_text(self.source, "source"))
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser un nivel válido.")
        if not isinstance(self.recorded_at, datetime):
            raise DomainValidationError("recorded_at debe ser una fecha válida.")
        if self.recorded_at.tzinfo is None:
            raise DomainValidationError("recorded_at debe incluir zona horaria.")
        object.__setattr__(self, "version", optional_text(self.version, "version"))

    def __eq__(self, other):
        if not isinstance(other, Result):
            return NotImplemented
        return self.result_id == other.result_id

    def __hash__(self):
        return hash(self.result_id)

    def to_dict(self):
        return {
            "result_id": self.result_id,
            "name": self.name,
            "value": _serialize_value(self.value),
            "evidence_type": self.evidence_type.value,
            "source": self.source,
            "confidence": self.confidence.value,
            "recorded_at": self.recorded_at.isoformat(),
            "version": self.version,
        }
