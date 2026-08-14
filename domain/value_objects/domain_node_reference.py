from dataclasses import dataclass, field
import json
from uuid import UUID, uuid5

from domain.entities._validation import optional_text, required_text
from domain.enums import GraphNodeType
from domain.exceptions import DomainValidationError
from domain.value_objects.frozen_mapping import FrozenMapping
from domain.value_objects.sensitive_data import contains_sensitive_key


_NODE_NAMESPACE = UUID("1e649930-3bd3-48ea-bd64-479bcfbb75e5")
def deterministic_node_id(node_type, domain_id, version=None):
    payload = json.dumps(
        {"type": node_type.value, "domain_id": domain_id, "version": version},
        sort_keys=True,
        separators=(",", ":"),
    )
    return str(uuid5(_NODE_NAMESPACE, payload))


@dataclass(frozen=True, slots=True)
class DomainNodeReference:
    """Referencia mínima a una entidad/contrato canónico, nunca una copia."""

    node_type: GraphNodeType
    domain_id: str
    label: str | None = None
    version: str | None = None
    metadata: FrozenMapping = field(default_factory=FrozenMapping)
    node_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.node_type, GraphNodeType):
            raise DomainValidationError("node_type debe ser GraphNodeType.")
        domain_id = required_text(self.domain_id, "domain_id")
        version = optional_text(self.version, "version")
        metadata = self.metadata
        if not isinstance(metadata, FrozenMapping):
            metadata = FrozenMapping.from_mapping(metadata)
        if contains_sensitive_key(metadata):
            raise DomainValidationError("metadata no puede contener datos sensibles.")
        expected = deterministic_node_id(self.node_type, domain_id, version)
        if self.node_id is not None and self.node_id != expected:
            raise DomainValidationError("node_id no coincide con la identidad determinista.")
        object.__setattr__(self, "domain_id", domain_id)
        object.__setattr__(self, "label", optional_text(self.label, "label"))
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "node_id", expected)

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "domain_id": self.domain_id,
            "label": self.label,
            "version": self.version,
            "metadata": self.metadata.to_dict(),
        }
