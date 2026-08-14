from dataclasses import dataclass
import json
from uuid import UUID, uuid5

from domain.entities._validation import optional_text, required_text
from domain.enums import EvidenceType, ResearchQuestionStatus
from domain.exceptions import DomainValidationError
from domain.value_objects.region import Region


_NAMESPACE = UUID("0f344e5b-c5f6-4860-86ab-89336257b269")


@dataclass(frozen=True, slots=True)
class ResearchQuestion:
    research_need_id: str
    question: str
    subject_type: str
    subject_id: str
    expected_evidence: tuple[EvidenceType, ...]
    status: ResearchQuestionStatus
    region: Region | None = None
    marketplace_id: str | None = None
    time_scope: str | None = None
    semantic_version: str = "1"
    question_id: str | None = None

    def __post_init__(self):
        for field in ("research_need_id", "question", "subject_type", "subject_id", "semantic_version"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        values = tuple(dict.fromkeys(self.expected_evidence))
        if not values or any(not isinstance(item, EvidenceType) for item in values):
            raise DomainValidationError("expected_evidence debe ser válido.")
        object.__setattr__(self, "expected_evidence", values)
        if not isinstance(self.status, ResearchQuestionStatus):
            raise DomainValidationError("status debe ser válido.")
        if self.region is not None and not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser Region.")
        for field in ("marketplace_id", "time_scope"):
            object.__setattr__(self, field, optional_text(getattr(self, field), field))
        semantic = json.dumps({"need": self.research_need_id, "question": self.question, "subject": [self.subject_type, self.subject_id], "region": self.region.to_dict() if self.region else None, "marketplace": self.marketplace_id, "time_scope": self.time_scope, "version": self.semantic_version}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        expected = str(uuid5(_NAMESPACE, semantic))
        if self.question_id is not None and self.question_id != expected:
            raise DomainValidationError("question_id no coincide con la pregunta semántica.")
        object.__setattr__(self, "question_id", expected)

    def to_dict(self):
        return {"question_id": self.question_id, "research_need_id": self.research_need_id, "question": self.question, "subject_type": self.subject_type, "subject_id": self.subject_id, "expected_evidence": [item.value for item in self.expected_evidence], "region": self.region.to_dict() if self.region else None, "marketplace_id": self.marketplace_id, "time_scope": self.time_scope, "status": self.status.value, "semantic_version": self.semantic_version}
