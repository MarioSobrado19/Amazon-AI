from dataclasses import dataclass, field

from domain.entities._validation import optional_text, required_text
from domain.entities.objective import Objective
from domain.exceptions import DomainValidationError
from domain.value_objects import FrozenMapping, GoalContextSnapshot


@dataclass(frozen=True, slots=True)
class GoalToBusinessRequest:
    """Solicitud de exploración; no genera ni persiste caminos por sí misma."""

    objective: Objective
    context: GoalContextSnapshot
    contract_version: str
    project_id: str | None = None
    additional_context: FrozenMapping = field(default_factory=FrozenMapping)

    def __post_init__(self):
        if not isinstance(self.objective, Objective):
            raise DomainValidationError("objective debe ser un Objective válido.")
        if not isinstance(self.context, GoalContextSnapshot):
            raise DomainValidationError(
                "context debe ser un GoalContextSnapshot válido."
            )
        if self.context.objective_id != self.objective.objective_id:
            raise DomainValidationError(
                "context debe pertenecer al mismo Objective de la solicitud."
            )
        object.__setattr__(
            self,
            "contract_version",
            required_text(self.contract_version, "contract_version"),
        )
        object.__setattr__(
            self, "project_id", optional_text(self.project_id, "project_id")
        )
        if not isinstance(self.additional_context, FrozenMapping):
            object.__setattr__(
                self,
                "additional_context",
                FrozenMapping.from_mapping(self.additional_context),
            )

    def to_dict(self):
        return {
            "objective": self.objective.to_dict(),
            "context": self.context.to_dict(),
            "project_id": self.project_id,
            "additional_context": self.additional_context.to_dict(),
            "contract_version": self.contract_version,
        }
