from dataclasses import dataclass
import json
from uuid import UUID, uuid5

from domain.entities._marketplace_validation import required_text, text_tuple
from domain.enums import EvidenceType, ResearchCategory
from domain.exceptions import DomainValidationError


_NAMESPACE = UUID("bc254ee4-0751-495b-bd35-d9d8a1ee8f10")


@dataclass(frozen=True, slots=True)
class ResearchNeed:
    """Declara qué falta saber; blocking no evalúa negativamente el sujeto."""

    subject_type: str
    subject_id: str
    category: ResearchCategory
    reason: str
    importance: str
    blocking: bool
    required_evidence_types: tuple[EvidenceType, ...]
    known_information: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    semantic_version: str = "1"
    need_id: str | None = None

    def __post_init__(self):
        for field in ("subject_type", "subject_id", "reason", "importance", "semantic_version"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if not isinstance(self.category, ResearchCategory):
            raise DomainValidationError("category debe ser ResearchCategory.")
        if not isinstance(self.blocking, bool):
            raise DomainValidationError("blocking debe ser booleano.")
        types = tuple(dict.fromkeys(self.required_evidence_types))
        if not types or any(not isinstance(item, EvidenceType) for item in types):
            raise DomainValidationError("required_evidence_types debe declarar evidencia válida.")
        object.__setattr__(self, "required_evidence_types", types)
        object.__setattr__(self, "known_information", tuple(sorted(text_tuple(self.known_information, "known_information"))))
        object.__setattr__(self, "missing_information", tuple(sorted(text_tuple(self.missing_information, "missing_information"))))
        semantic = json.dumps({"subject_type": self.subject_type, "subject_id": self.subject_id, "category": self.category.value, "reason": self.reason, "version": self.semantic_version}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        expected = str(uuid5(_NAMESPACE, semantic))
        if self.need_id is not None and self.need_id != expected:
            raise DomainValidationError("need_id no coincide con la necesidad semántica.")
        object.__setattr__(self, "need_id", expected)

    def to_dict(self):
        return {"need_id": self.need_id, "subject_type": self.subject_type, "subject_id": self.subject_id, "category": self.category.value, "reason": self.reason, "importance": self.importance, "blocking": self.blocking, "required_evidence_types": [item.value for item in self.required_evidence_types], "known_information": list(self.known_information), "missing_information": list(self.missing_information), "semantic_version": self.semantic_version}
