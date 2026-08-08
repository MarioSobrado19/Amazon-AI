from dataclasses import dataclass

from domain.entities import OpportunityScenario, Result
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class OpportunityScenarioResult:
    """Resultados inmutables asociados a un contexto operativo concreto."""

    scenario: OpportunityScenario
    results: tuple[Result, ...]

    def __post_init__(self):
        if not isinstance(self.scenario, OpportunityScenario):
            raise DomainValidationError("scenario debe ser OpportunityScenario válido.")
        results = tuple(self.results)
        if not results:
            raise DomainValidationError("results debe contener al menos un resultado.")
        if any(not isinstance(item, Result) for item in results):
            raise DomainValidationError("results debe contener Result válidos.")
        object.__setattr__(self, "results", results)

    def to_dict(self):
        return {
            "scenario": self.scenario.to_dict(),
            "results": [item.to_dict() for item in self.results],
        }

