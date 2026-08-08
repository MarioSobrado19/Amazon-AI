from dataclasses import dataclass
from datetime import datetime

from domain.entities._marketplace_validation import aware_datetime, optional_text, required_text
from domain.entities._identity import internal_id
from domain.entities.business_model import BusinessModel
from domain.entities.marketplace import Marketplace
from domain.entities.marketplace_condition_snapshot import MarketplaceConditionSnapshot
from domain.entities.opportunity import Opportunity
from domain.entities.result import Result
from domain.enums import EvidenceType
from domain.exceptions import DomainValidationError
from domain.value_objects import Region


@dataclass(frozen=True, slots=True, eq=False)
class OpportunityScenario:
    """Contexto histórico con identidad propia para una Opportunity sin mutarla."""

    scenario_id: str
    opportunity: Opportunity
    marketplace: Marketplace
    business_model: BusinessModel
    region: Region
    evaluated_at: datetime
    supplier_id: str | None = None
    conditions: tuple[MarketplaceConditionSnapshot, ...] = ()
    costs: tuple[Result, ...] = ()
    assumptions: tuple[Result, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "scenario_id", internal_id(self.scenario_id, "scenario_id"))
        if not isinstance(self.opportunity, Opportunity):
            raise DomainValidationError("opportunity debe ser una Opportunity válida.")
        if not isinstance(self.marketplace, Marketplace):
            raise DomainValidationError("marketplace debe ser un Marketplace válido.")
        if not isinstance(self.business_model, BusinessModel):
            raise DomainValidationError("business_model debe ser un BusinessModel válido.")
        if not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser una Region válida.")
        if self.region.country_code != self.marketplace.region.country_code:
            raise DomainValidationError("region debe pertenecer al país del marketplace.")
        if self.region.country_code != self.business_model.region.country_code:
            raise DomainValidationError("region debe pertenecer al país del business model.")
        if (
            self.business_model.marketplace_id is not None
            and self.business_model.marketplace_id != self.marketplace.marketplace_id
        ):
            raise DomainValidationError("business_model pertenece a otro marketplace.")
        object.__setattr__(
            self, "supplier_id", optional_text(self.supplier_id, "supplier_id")
        )
        conditions = tuple(self.conditions)
        if any(not isinstance(item, MarketplaceConditionSnapshot) for item in conditions):
            raise DomainValidationError("conditions debe contener snapshots válidos.")
        if any(
            item.marketplace.marketplace_id != self.marketplace.marketplace_id
            or item.region.country_code != self.region.country_code
            for item in conditions
        ):
            raise DomainValidationError("conditions no corresponde al contexto del escenario.")
        object.__setattr__(self, "conditions", conditions)
        costs = tuple(self.costs)
        if any(not isinstance(item, Result) for item in costs):
            raise DomainValidationError("costs debe contener Result válidos.")
        object.__setattr__(self, "costs", costs)
        assumptions = tuple(self.assumptions)
        if any(not isinstance(item, Result) for item in assumptions):
            raise DomainValidationError("assumptions debe contener Result válidos.")
        if any(item.evidence_type is not EvidenceType.ASSUMPTION for item in assumptions):
            raise DomainValidationError("assumptions debe declarar EvidenceType.ASSUMPTION.")
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(
            self, "evaluated_at", aware_datetime(self.evaluated_at, "evaluated_at")
        )

    def __eq__(self, other):
        if not isinstance(other, OpportunityScenario):
            return NotImplemented
        return self.scenario_id == other.scenario_id

    def __hash__(self):
        return hash(self.scenario_id)

    def to_dict(self):
        return {
            "scenario_id": self.scenario_id,
            "opportunity": self.opportunity.to_dict(),
            "marketplace": self.marketplace.to_dict(),
            "business_model": self.business_model.to_dict(),
            "region": self.region.to_dict(),
            "supplier_id": self.supplier_id,
            "conditions": [item.to_dict() for item in self.conditions],
            "costs": [item.to_dict() for item in self.costs],
            "assumptions": [item.to_dict() for item in self.assumptions],
            "evaluated_at": self.evaluated_at.isoformat(),
        }
