from dataclasses import dataclass
from datetime import datetime

from domain.entities._identity import internal_id
from domain.entities._marketplace_validation import aware_datetime, required_text, text_tuple
from domain.enums import ConfidenceLevel, EvidenceType
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True, eq=False)
class ResearchFinding:
    """Interpretación limitada: nunca se representa como DATA."""

    finding_id: str
    investigation_id: str
    statement: str
    evidence_ids: tuple[str, ...]
    interpretation_type: EvidenceType
    confidence: ConfidenceLevel
    limitations: tuple[str, ...]
    created_at: datetime
    version: str

    def __post_init__(self):
        object.__setattr__(self, "finding_id", internal_id(self.finding_id, "finding_id"))
        object.__setattr__(self, "investigation_id", internal_id(self.investigation_id, "investigation_id"))
        object.__setattr__(self, "statement", required_text(self.statement, "statement"))
        ids = tuple(dict.fromkeys(required_text(item, "evidence_id") for item in self.evidence_ids))
        object.__setattr__(self, "evidence_ids", ids)
        if self.interpretation_type is EvidenceType.DATA:
            raise DomainValidationError("Un Finding es interpretación y nunca puede ser DATA.")
        if not ids and self.interpretation_type is not EvidenceType.ASSUMPTION:
            raise DomainValidationError("Finding sin evidencia debe declararse ASSUMPTION.")
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser válido.")
        object.__setattr__(self, "limitations", tuple(sorted(text_tuple(self.limitations, "limitations"))))
        object.__setattr__(self, "created_at", aware_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "version", required_text(self.version, "version"))

    def __eq__(self, other):
        return isinstance(other, ResearchFinding) and self.finding_id == other.finding_id

    def __hash__(self):
        return hash(self.finding_id)

    def to_dict(self):
        return {"finding_id": self.finding_id, "investigation_id": self.investigation_id, "statement": self.statement, "evidence_ids": list(self.evidence_ids), "interpretation_type": self.interpretation_type.value, "confidence": self.confidence.value, "limitations": list(self.limitations), "created_at": self.created_at.isoformat(), "version": self.version}
