from dataclasses import dataclass
from datetime import datetime

from domain.entities._identity import internal_id
from domain.entities._marketplace_validation import aware_datetime, optional_aware_datetime, optional_text, required_text, text_tuple
from domain.enums import ConfidenceLevel, EvidenceType, FreshnessStatus, ResearchCategory, VerificationStatus
from domain.exceptions import DomainValidationError
from domain.value_objects import FrozenMapping, Region
from domain.value_objects.sensitive_data import (
    contains_sensitive_key,
    contains_sensitive_reference,
)


@dataclass(frozen=True, slots=True, eq=False)
class EvidenceRecord:
    """Observación histórica; dos recuperaciones son registros independientes."""

    evidence_id: str
    subject_type: str
    subject_id: str
    category: ResearchCategory
    evidence_type: EvidenceType
    value: FrozenMapping
    source: str
    observed_at: datetime
    retrieved_at: datetime
    freshness: FreshnessStatus
    verification_status: VerificationStatus
    confidence: ConfidenceLevel
    version: str
    source_reference: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    region: Region | None = None
    marketplace_id: str | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "evidence_id", internal_id(self.evidence_id, "evidence_id"))
        for field in ("subject_type", "subject_id", "source", "version"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if not isinstance(self.category, ResearchCategory) or not isinstance(self.evidence_type, EvidenceType):
            raise DomainValidationError("category y evidence_type deben ser válidos.")
        value = self.value if isinstance(self.value, FrozenMapping) else FrozenMapping.from_mapping(self.value)
        if contains_sensitive_key(value):
            raise DomainValidationError("value no puede contener secretos o PII sensible.")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "observed_at", aware_datetime(self.observed_at, "observed_at"))
        object.__setattr__(self, "retrieved_at", aware_datetime(self.retrieved_at, "retrieved_at"))
        object.__setattr__(self, "valid_from", optional_aware_datetime(self.valid_from, "valid_from"))
        object.__setattr__(self, "valid_until", optional_aware_datetime(self.valid_until, "valid_until"))
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise DomainValidationError("valid_until no puede preceder valid_from.")
        if not isinstance(self.freshness, FreshnessStatus) or not isinstance(self.verification_status, VerificationStatus) or not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("freshness, verification_status y confidence deben ser válidos.")
        if self.region is not None and not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser Region.")
        for field in ("source_reference", "marketplace_id"):
            object.__setattr__(self, field, optional_text(getattr(self, field), field))
        if contains_sensitive_reference(self.source_reference):
            raise DomainValidationError("source_reference no puede contener credenciales.")
        object.__setattr__(self, "limitations", tuple(sorted(text_tuple(self.limitations, "limitations"))))

    def __eq__(self, other):
        return isinstance(other, EvidenceRecord) and self.evidence_id == other.evidence_id

    def __hash__(self):
        return hash(self.evidence_id)

    def to_dict(self):
        return {"evidence_id": self.evidence_id, "subject_type": self.subject_type, "subject_id": self.subject_id, "category": self.category.value, "evidence_type": self.evidence_type.value, "value": self.value.to_dict(), "source": self.source, "source_reference": self.source_reference, "observed_at": self.observed_at.isoformat(), "retrieved_at": self.retrieved_at.isoformat(), "valid_from": self.valid_from.isoformat() if self.valid_from else None, "valid_until": self.valid_until.isoformat() if self.valid_until else None, "freshness": self.freshness.value, "verification_status": self.verification_status.value, "confidence": self.confidence.value, "region": self.region.to_dict() if self.region else None, "marketplace_id": self.marketplace_id, "version": self.version, "limitations": list(self.limitations)}
