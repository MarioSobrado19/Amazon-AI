from dataclasses import dataclass
from datetime import datetime
import json
from uuid import UUID, uuid5

from domain.entities._marketplace_validation import aware_datetime, required_text
from domain.enums import ConflictResolutionStatus, ResearchCategory
from domain.exceptions import DomainValidationError


_NAMESPACE = UUID("97a9825b-50ee-4ed2-9bb2-0aa11993d092")


@dataclass(frozen=True, slots=True)
class EvidenceConflict:
    """Conserva contradicciones sin seleccionar evidencia ganadora."""

    subject_type: str
    subject_id: str
    category: ResearchCategory
    evidence_ids: tuple[str, ...]
    reason: str
    resolution_status: ConflictResolutionStatus
    created_at: datetime
    conflict_id: str | None = None

    def __post_init__(self):
        for field in ("subject_type", "subject_id", "reason"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if not isinstance(self.category, ResearchCategory) or not isinstance(self.resolution_status, ConflictResolutionStatus):
            raise DomainValidationError("category y resolution_status deben ser válidos.")
        ids = tuple(sorted(set(required_text(item, "evidence_id") for item in self.evidence_ids)))
        if len(ids) < 2:
            raise DomainValidationError("Un conflicto requiere al menos dos evidencias.")
        object.__setattr__(self, "evidence_ids", ids)
        object.__setattr__(self, "created_at", aware_datetime(self.created_at, "created_at"))
        canonical = json.dumps({"subject": [self.subject_type, self.subject_id], "category": self.category.value, "evidence_ids": ids}, sort_keys=True, separators=(",", ":"))
        expected = str(uuid5(_NAMESPACE, canonical))
        if self.conflict_id is not None and self.conflict_id != expected:
            raise DomainValidationError("conflict_id no coincide con el conflicto semántico.")
        object.__setattr__(self, "conflict_id", expected)

    def to_dict(self):
        return {"conflict_id": self.conflict_id, "subject_type": self.subject_type, "subject_id": self.subject_id, "category": self.category.value, "evidence_ids": list(self.evidence_ids), "reason": self.reason, "resolution_status": self.resolution_status.value, "created_at": self.created_at.isoformat()}
