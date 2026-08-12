from dataclasses import dataclass
from datetime import datetime

from domain.entities._identity import internal_id
from domain.entities._marketplace_validation import aware_datetime, required_text, text_tuple
from domain.entities.result import Result
from domain.enums import BusinessPathState
from domain.exceptions import DomainValidationError
from domain.value_objects import GoalContextSnapshot


@dataclass(frozen=True, slots=True, eq=False)
class BusinessPath:
    """Ruta persistente elegida por una persona; referencia, no copia, escenarios."""

    business_path_id: str
    objective_id: str
    source_candidate_id: str
    context: GoalContextSnapshot
    scenario_ids: tuple[str, ...]
    marketplace_ids: tuple[str, ...]
    business_model_ids: tuple[str, ...]
    condition_snapshot_ids: tuple[str, ...]
    state: BusinessPathState
    available_evidence: tuple[Result, ...]
    missing_evidence: tuple[str, ...]
    constraints: tuple[str, ...]
    risks: tuple[str, ...]
    assumptions: tuple[Result, ...]
    next_steps: tuple[str, ...]
    created_at: datetime
    last_evaluated_at: datetime
    version: int
    retained_by: str
    state_change_reason: str
    supersedes_version: int | None = None

    def __post_init__(self):
        object.__setattr__(self, "business_path_id", internal_id(self.business_path_id, "business_path_id"))
        object.__setattr__(self, "source_candidate_id", internal_id(self.source_candidate_id, "source_candidate_id"))
        for field in ("objective_id", "retained_by", "state_change_reason"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if not isinstance(self.context, GoalContextSnapshot) or self.context.objective_id != self.objective_id:
            raise DomainValidationError("context debe pertenecer al objetivo de BusinessPath.")
        if not isinstance(self.state, BusinessPathState):
            raise DomainValidationError("state debe ser BusinessPathState válido.")
        for field in ("scenario_ids", "marketplace_ids", "business_model_ids", "condition_snapshot_ids"):
            values = tuple(internal_id(value, field) for value in getattr(self, field))
            if len(values) != len(set(values)):
                raise DomainValidationError(f"{field} contiene referencias duplicadas.")
            object.__setattr__(self, field, values)
        for field in ("missing_evidence", "constraints", "risks", "next_steps"):
            object.__setattr__(self, field, text_tuple(getattr(self, field), field))
        for field in ("available_evidence", "assumptions"):
            values = tuple(getattr(self, field))
            if any(not isinstance(item, Result) for item in values):
                raise DomainValidationError(f"{field} contiene Result inválidos.")
            object.__setattr__(self, field, values)
        object.__setattr__(self, "created_at", aware_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "last_evaluated_at", aware_datetime(self.last_evaluated_at, "last_evaluated_at"))
        if self.last_evaluated_at < self.created_at:
            raise DomainValidationError("last_evaluated_at no puede preceder created_at.")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise DomainValidationError("version debe ser un entero positivo.")
        if self.supersedes_version is not None:
            if isinstance(self.supersedes_version, bool) or self.supersedes_version != self.version - 1:
                raise DomainValidationError("supersedes_version debe ser la versión anterior.")

    def __eq__(self, other):
        if not isinstance(other, BusinessPath):
            return NotImplemented
        return self.business_path_id == other.business_path_id

    def __hash__(self):
        return hash(self.business_path_id)

    def to_dict(self):
        return {
            "business_path_id": self.business_path_id,
            "objective_id": self.objective_id,
            "source_candidate_id": self.source_candidate_id,
            "context": self.context.to_dict(),
            "scenario_ids": list(self.scenario_ids),
            "marketplace_ids": list(self.marketplace_ids),
            "business_model_ids": list(self.business_model_ids),
            "condition_snapshot_ids": list(self.condition_snapshot_ids),
            "state": self.state.value,
            "available_evidence": [item.to_dict() for item in self.available_evidence],
            "missing_evidence": list(self.missing_evidence),
            "constraints": list(self.constraints),
            "risks": list(self.risks),
            "assumptions": [item.to_dict() for item in self.assumptions],
            "next_steps": list(self.next_steps),
            "created_at": self.created_at.isoformat(),
            "last_evaluated_at": self.last_evaluated_at.isoformat(),
            "version": self.version,
            "retained_by": self.retained_by,
            "state_change_reason": self.state_change_reason,
            "supersedes_version": self.supersedes_version,
        }
