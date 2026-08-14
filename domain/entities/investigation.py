from dataclasses import dataclass
from datetime import datetime

from domain.entities._identity import internal_id
from domain.entities._marketplace_validation import aware_datetime, optional_text, required_text, text_tuple
from domain.enums import InvestigationStatus
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True, eq=False)
class Investigation:
    """Investigación persistente/versionada que referencia preguntas y hallazgos."""

    investigation_id: str
    subject_type: str
    subject_id: str
    status: InvestigationStatus
    question_ids: tuple[str, ...]
    finding_ids: tuple[str, ...]
    missing_information: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    version: int
    project_id: str | None = None
    business_path_id: str | None = None
    opportunity_id: str | None = None
    scenario_id: str | None = None
    supersedes_version: int | None = None

    def __post_init__(self):
        object.__setattr__(self, "investigation_id", internal_id(self.investigation_id, "investigation_id"))
        for field in ("subject_type", "subject_id"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if not isinstance(self.status, InvestigationStatus):
            raise DomainValidationError("status debe ser InvestigationStatus.")
        for field in ("question_ids", "finding_ids", "missing_information"):
            object.__setattr__(self, field, tuple(dict.fromkeys(text_tuple(getattr(self, field), field))))
        for field in ("project_id", "business_path_id", "opportunity_id", "scenario_id"):
            object.__setattr__(self, field, optional_text(getattr(self, field), field))
        object.__setattr__(self, "created_at", aware_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", aware_datetime(self.updated_at, "updated_at"))
        if self.updated_at < self.created_at:
            raise DomainValidationError("updated_at no puede preceder created_at.")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise DomainValidationError("version debe ser entero positivo.")
        if self.supersedes_version is not None and self.supersedes_version != self.version - 1:
            raise DomainValidationError("supersedes_version debe ser la versión anterior.")

    def __eq__(self, other):
        return isinstance(other, Investigation) and self.investigation_id == other.investigation_id

    def __hash__(self):
        return hash(self.investigation_id)

    def to_dict(self):
        return {"investigation_id": self.investigation_id, "subject_type": self.subject_type, "subject_id": self.subject_id, "project_id": self.project_id, "business_path_id": self.business_path_id, "opportunity_id": self.opportunity_id, "scenario_id": self.scenario_id, "status": self.status.value, "question_ids": list(self.question_ids), "finding_ids": list(self.finding_ids), "missing_information": list(self.missing_information), "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat(), "version": self.version, "supersedes_version": self.supersedes_version}
