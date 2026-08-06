from dataclasses import dataclass

from domain.entities import Opportunity, Result
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class OpportunityResult:
    """Resultados calculados asociados a una oportunidad concreta."""

    opportunity: Opportunity
    results: tuple[Result, ...]

    def __post_init__(self):
        if not isinstance(self.opportunity, Opportunity):
            raise DomainValidationError("opportunity debe ser válida.")
        results = tuple(self.results)
        if not results:
            raise DomainValidationError("results debe contener al menos un resultado.")
        if any(not isinstance(item, Result) for item in results):
            raise DomainValidationError("results debe contener Result válidos.")
        object.__setattr__(self, "results", results)

    def to_dict(self):
        return {
            "opportunity": self.opportunity.to_dict(),
            "results": [item.to_dict() for item in self.results],
        }

