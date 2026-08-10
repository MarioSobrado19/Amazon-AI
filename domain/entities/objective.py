from dataclasses import dataclass

from domain.entities._validation import optional_text, required_text


@dataclass(frozen=True, slots=True, eq=False)
class Objective:
    """Intención declarada que sirve como raíz de Goal-to-Business."""

    objective_id: str
    description: str
    objective_type: str | None = None

    def __post_init__(self):
        object.__setattr__(
            self, "objective_id", required_text(self.objective_id, "objective_id")
        )
        object.__setattr__(
            self, "description", required_text(self.description, "description")
        )
        object.__setattr__(
            self,
            "objective_type",
            optional_text(self.objective_type, "objective_type"),
        )

    def __eq__(self, other):
        if not isinstance(other, Objective):
            return NotImplemented
        return self.objective_id == other.objective_id

    def __hash__(self):
        return hash(self.objective_id)

    def to_dict(self):
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "objective_type": self.objective_type,
        }
