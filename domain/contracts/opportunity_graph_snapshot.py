from dataclasses import dataclass
from datetime import datetime
import json
from uuid import UUID, uuid5

from domain.contracts.evidence_relation import EvidenceRelation
from domain.entities._marketplace_validation import aware_datetime, required_text, text_tuple
from domain.exceptions import DomainValidationError
from domain.value_objects import DomainNodeReference


_GRAPH_NAMESPACE = UUID("f225478c-780e-4d66-94a3-240584f28adc")


def _graph_id(root_node, nodes, relations, missing, warnings, graph_version, projector_version):
    semantic = {
        "root": root_node.node_id,
        "nodes": sorted(node.node_id for node in nodes),
        "relations": sorted(relation.relation_id for relation in relations),
        "missing": sorted(missing),
        "warnings": sorted(warnings),
        "graph_version": graph_version,
        "projector_version": projector_version,
    }
    canonical = json.dumps(semantic, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return str(uuid5(_GRAPH_NAMESPACE, canonical))


@dataclass(frozen=True, slots=True)
class OpportunityGraphSnapshot:
    """Proyección reconstruible; generated_at no forma parte de su identidad semántica."""

    root_node: DomainNodeReference
    nodes: tuple[DomainNodeReference, ...]
    relations: tuple[EvidenceRelation, ...]
    missing_information: tuple[str, ...]
    warnings: tuple[str, ...]
    generated_at: datetime
    graph_version: str
    projector_version: str
    graph_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.root_node, DomainNodeReference):
            raise DomainValidationError("root_node debe ser una referencia válida.")
        nodes = tuple(sorted(tuple(self.nodes), key=lambda item: item.node_id))
        relations = tuple(sorted(tuple(self.relations), key=lambda item: item.relation_id))
        if any(not isinstance(item, DomainNodeReference) for item in nodes):
            raise DomainValidationError("nodes contiene referencias inválidas.")
        if any(not isinstance(item, EvidenceRelation) for item in relations):
            raise DomainValidationError("relations contiene relaciones inválidas.")
        if len({item.node_id for item in nodes}) != len(nodes):
            raise DomainValidationError("nodes contiene duplicados.")
        if len({item.relation_id for item in relations}) != len(relations):
            raise DomainValidationError("relations contiene duplicados.")
        if self.root_node.node_id not in {item.node_id for item in nodes}:
            raise DomainValidationError("root_node debe estar incluido en nodes.")
        known = {item.node_id for item in nodes}
        if any(item.source_node.node_id not in known or item.target_node.node_id not in known for item in relations):
            raise DomainValidationError("Todas las relaciones deben referenciar nodos del snapshot.")
        missing = text_tuple(self.missing_information, "missing_information")
        warnings = text_tuple(self.warnings, "warnings")
        graph_version = required_text(self.graph_version, "graph_version")
        projector_version = required_text(self.projector_version, "projector_version")
        generated_at = aware_datetime(self.generated_at, "generated_at")
        expected = _graph_id(self.root_node, nodes, relations, missing, warnings, graph_version, projector_version)
        if self.graph_id is not None and self.graph_id != expected:
            raise DomainValidationError("graph_id no coincide con el contenido semántico.")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "relations", relations)
        object.__setattr__(self, "missing_information", missing)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "generated_at", generated_at)
        object.__setattr__(self, "graph_version", graph_version)
        object.__setattr__(self, "projector_version", projector_version)
        object.__setattr__(self, "graph_id", expected)

    def to_dict(self):
        return {
            "graph_id": self.graph_id,
            "root_node": self.root_node.to_dict(),
            "nodes": [item.to_dict() for item in self.nodes],
            "relations": [item.to_dict() for item in self.relations],
            "missing_information": list(self.missing_information),
            "warnings": list(self.warnings),
            "generated_at": self.generated_at.isoformat(),
            "graph_version": self.graph_version,
            "projector_version": self.projector_version,
        }
