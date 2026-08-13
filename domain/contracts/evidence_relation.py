from dataclasses import dataclass
from datetime import datetime
import json
from uuid import UUID, uuid5

from domain.entities._marketplace_validation import aware_datetime, required_text, text_tuple
from domain.enums import (
    ConfidenceLevel,
    EvidenceRelationType,
    EvidenceType,
    FreshnessStatus,
)
from domain.exceptions import DomainValidationError
from domain.value_objects import DomainNodeReference


_RELATION_NAMESPACE = UUID("4dc65890-a9fd-444c-a662-52b7c0e204fe")


def _relation_id(values):
    canonical = json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return str(uuid5(_RELATION_NAMESPACE, canonical))


@dataclass(frozen=True, slots=True)
class EvidenceRelation:
    """Arista dirigida y trazable.

    ``provides_evidence_for`` solo declara que un Result aporta evidencia al
    contexto del nodo destino. No valida rentabilidad, conveniencia, causalidad,
    compatibilidad ni recomendación alguna.
    """

    source_node: DomainNodeReference
    target_node: DomainNodeReference
    relation_type: EvidenceRelationType
    evidence_type: EvidenceType
    source: str
    confidence: ConfidenceLevel
    evaluated_at: datetime
    explanation: str
    version: str
    freshness: FreshnessStatus | None = None
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    relation_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.source_node, DomainNodeReference) or not isinstance(self.target_node, DomainNodeReference):
            raise DomainValidationError("source_node y target_node deben ser referencias válidas.")
        if self.source_node.node_id == self.target_node.node_id:
            raise DomainValidationError("Una relación no puede apuntar al mismo nodo.")
        if not isinstance(self.relation_type, EvidenceRelationType):
            raise DomainValidationError("relation_type debe ser válido.")
        if not isinstance(self.evidence_type, EvidenceType):
            raise DomainValidationError("evidence_type debe ser válido.")
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser válido.")
        if self.freshness is not None and not isinstance(self.freshness, FreshnessStatus):
            raise DomainValidationError("freshness debe ser válido.")
        object.__setattr__(self, "source", required_text(self.source, "source"))
        object.__setattr__(self, "explanation", required_text(self.explanation, "explanation"))
        object.__setattr__(self, "version", required_text(self.version, "version"))
        object.__setattr__(self, "evaluated_at", aware_datetime(self.evaluated_at, "evaluated_at"))
        object.__setattr__(
            self, "assumptions", tuple(sorted(text_tuple(self.assumptions, "assumptions")))
        )
        object.__setattr__(
            self, "limitations", tuple(sorted(text_tuple(self.limitations, "limitations")))
        )
        semantic = {
            "source_node": self.source_node.node_id,
            "target_node": self.target_node.node_id,
            "type": self.relation_type.value,
            "evidence_type": self.evidence_type.value,
            "source": self.source,
            "confidence": self.confidence.value,
            "evaluated_at": self.evaluated_at.isoformat(),
            "freshness": self.freshness.value if self.freshness else None,
            "explanation": self.explanation,
            "assumptions": self.assumptions,
            "limitations": self.limitations,
            "version": self.version,
        }
        expected = _relation_id(semantic)
        if self.relation_id is not None and self.relation_id != expected:
            raise DomainValidationError("relation_id no coincide con la semántica de la relación.")
        object.__setattr__(self, "relation_id", expected)

    def to_dict(self):
        return {
            "relation_id": self.relation_id,
            "source_node": self.source_node.to_dict(),
            "target_node": self.target_node.to_dict(),
            "relation_type": self.relation_type.value,
            "evidence_type": self.evidence_type.value,
            "source": self.source,
            "confidence": self.confidence.value,
            "evaluated_at": self.evaluated_at.isoformat(),
            "freshness": self.freshness.value if self.freshness else None,
            "explanation": self.explanation,
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
            "version": self.version,
        }
