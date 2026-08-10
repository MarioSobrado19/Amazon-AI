from dataclasses import dataclass
from decimal import Decimal

from domain.entities._validation import optional_text, required_text
from domain.enums import InformationSource
from domain.value_objects._goal_context_validation import (
    declared_source,
    optional_scalar,
    serialize_scalar,
)


@dataclass(frozen=True, slots=True)
class PreferenceDeclaration:
    """Preferencia no vinculante; nunca equivale a una restricción."""

    preference_type: str
    value: str | bool | Decimal | None = None
    explanation: str | None = None
    source: InformationSource = InformationSource.USER_DECLARED

    def __post_init__(self):
        object.__setattr__(
            self,
            "preference_type",
            required_text(self.preference_type, "preference_type"),
        )
        object.__setattr__(self, "value", optional_scalar(self.value, "value"))
        object.__setattr__(
            self, "explanation", optional_text(self.explanation, "explanation")
        )
        declared_source(self.source)

    @property
    def is_binding(self):
        return False

    def to_dict(self):
        return {
            "declaration_kind": "preference",
            "preference_type": self.preference_type,
            "value": serialize_scalar(self.value),
            "explanation": self.explanation,
            "source": self.source.value,
            "is_binding": False,
        }
