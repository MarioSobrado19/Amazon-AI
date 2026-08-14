from dataclasses import dataclass
from datetime import datetime

from domain.contracts.evidence_conflict import EvidenceConflict
from domain.entities import EvidenceRecord, Investigation, ResearchFinding
from domain.entities._marketplace_validation import aware_datetime, required_text, text_tuple
from domain.enums import ConfidenceLevel
from domain.exceptions import DomainValidationError
from domain.value_objects import ResearchNeed, ResearchQuestion


@dataclass(frozen=True, slots=True)
class ResearchAssessment:
    """Estado del conocimiento; no contiene recomendación ni decisión."""

    investigation: Investigation
    needs: tuple[ResearchNeed, ...]
    questions: tuple[ResearchQuestion, ...]
    evidence: tuple[EvidenceRecord, ...]
    findings: tuple[ResearchFinding, ...]
    conflicts: tuple[EvidenceConflict, ...]
    verified_information: tuple[str, ...]
    unverified_information: tuple[str, ...]
    stale_information: tuple[str, ...]
    missing_information: tuple[str, ...]
    blocking_unknowns: tuple[str, ...]
    confidence: ConfidenceLevel
    limitations: tuple[str, ...]
    next_research_steps: tuple[str, ...]
    assessed_at: datetime
    version: str

    def __post_init__(self):
        if not isinstance(self.investigation, Investigation):
            raise DomainValidationError("investigation debe ser válida.")
        typed = (("needs", ResearchNeed), ("questions", ResearchQuestion), ("evidence", EvidenceRecord), ("findings", ResearchFinding), ("conflicts", EvidenceConflict))
        for field, kind in typed:
            values = tuple(getattr(self, field))
            if any(not isinstance(item, kind) for item in values):
                raise DomainValidationError(f"{field} contiene valores inválidos.")
            object.__setattr__(self, field, values)
        for field in ("verified_information", "unverified_information", "stale_information", "missing_information", "blocking_unknowns", "limitations", "next_research_steps"):
            object.__setattr__(self, field, tuple(sorted(text_tuple(getattr(self, field), field))))
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser válido.")
        object.__setattr__(self, "assessed_at", aware_datetime(self.assessed_at, "assessed_at"))
        object.__setattr__(self, "version", required_text(self.version, "version"))

    def to_dict(self):
        return {"investigation": self.investigation.to_dict(), "needs": [x.to_dict() for x in self.needs], "questions": [x.to_dict() for x in self.questions], "evidence": [x.to_dict() for x in self.evidence], "findings": [x.to_dict() for x in self.findings], "conflicts": [x.to_dict() for x in self.conflicts], "verified_information": list(self.verified_information), "unverified_information": list(self.unverified_information), "stale_information": list(self.stale_information), "missing_information": list(self.missing_information), "blocking_unknowns": list(self.blocking_unknowns), "confidence": self.confidence.value, "limitations": list(self.limitations), "next_research_steps": list(self.next_research_steps), "assessed_at": self.assessed_at.isoformat(), "version": self.version}
