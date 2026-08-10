from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from domain.entities._validation import optional_text, required_text
from domain.enums import InformationSource, RiskLevel
from domain.exceptions import DomainValidationError
from domain.value_objects._goal_context_validation import (
    aware_datetime,
    declared_source,
    optional_non_negative_decimal,
)
from domain.value_objects.capability_declaration import CapabilityDeclaration
from domain.value_objects.constraint_declaration import ConstraintDeclaration
from domain.value_objects.money import Money
from domain.value_objects.preference_declaration import PreferenceDeclaration
from domain.value_objects.region import Region
from domain.value_objects.resource_availability import ResourceAvailability


@dataclass(frozen=True, slots=True)
class GoalContextSnapshot:
    """Fotografía inmutable del contexto declarado para un Objetivo."""

    objective_id: str
    captured_at: datetime
    version: str
    source: InformationSource = InformationSource.USER_DECLARED
    available_budget: Money | None = None
    currency: str | None = None
    available_time_hours_per_week: Decimal | None = None
    experience: str | None = None
    risk_tolerance: RiskLevel | None = None
    region: Region | None = None
    business_stage: str | None = None
    logistics_capacity: str | None = None
    storage_space: str | None = None
    resources: tuple[ResourceAvailability, ...] = ()
    capabilities: tuple[CapabilityDeclaration, ...] = ()
    constraints: tuple[ConstraintDeclaration, ...] = ()
    preferences: tuple[PreferenceDeclaration, ...] = ()

    def __post_init__(self):
        object.__setattr__(
            self, "objective_id", required_text(self.objective_id, "objective_id")
        )
        object.__setattr__(self, "version", required_text(self.version, "version"))
        object.__setattr__(
            self, "captured_at", aware_datetime(self.captured_at, "captured_at")
        )
        declared_source(self.source)
        if self.available_budget is not None:
            if not isinstance(self.available_budget, Money):
                raise DomainValidationError("available_budget debe ser Money válido.")
            if self.available_budget.amount < 0:
                raise DomainValidationError("available_budget debe ser no negativo.")
        if self.currency is None:
            currency = self.available_budget.currency if self.available_budget else None
        elif not isinstance(self.currency, str):
            raise DomainValidationError("currency debe ser un código de tres letras.")
        else:
            currency = self.currency.strip().upper()
            if len(currency) != 3 or not currency.isalpha():
                raise DomainValidationError("currency debe ser un código de tres letras.")
        if self.available_budget is not None and currency != self.available_budget.currency:
            raise DomainValidationError(
                "currency debe coincidir con la moneda de available_budget."
            )
        object.__setattr__(self, "currency", currency)
        object.__setattr__(
            self,
            "available_time_hours_per_week",
            optional_non_negative_decimal(
                self.available_time_hours_per_week,
                "available_time_hours_per_week",
            ),
        )
        for field_name in (
            "experience",
            "business_stage",
            "logistics_capacity",
            "storage_space",
        ):
            object.__setattr__(
                self, field_name, optional_text(getattr(self, field_name), field_name)
            )
        if self.risk_tolerance is not None and not isinstance(
            self.risk_tolerance, RiskLevel
        ):
            raise DomainValidationError("risk_tolerance debe ser RiskLevel válido.")
        if self.region is not None and not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser Region válida.")
        self._freeze_typed("resources", ResourceAvailability)
        self._freeze_typed("capabilities", CapabilityDeclaration)
        self._freeze_typed("constraints", ConstraintDeclaration)
        self._freeze_typed("preferences", PreferenceDeclaration)

    def _freeze_typed(self, field_name, expected_type):
        values = tuple(getattr(self, field_name))
        if any(not isinstance(item, expected_type) for item in values):
            raise DomainValidationError(
                f"{field_name} debe contener {expected_type.__name__} válidos."
            )
        object.__setattr__(self, field_name, values)

    def missing_fields(self):
        scalar_fields = (
            "available_budget",
            "currency",
            "available_time_hours_per_week",
            "experience",
            "risk_tolerance",
            "region",
            "business_stage",
            "logistics_capacity",
            "storage_space",
        )
        return tuple(name for name in scalar_fields if getattr(self, name) is None)

    def to_dict(self):
        return {
            "objective_id": self.objective_id,
            "source": self.source.value,
            "available_budget": (
                self.available_budget.to_dict() if self.available_budget else None
            ),
            "currency": self.currency,
            "available_time_hours_per_week": (
                str(self.available_time_hours_per_week)
                if self.available_time_hours_per_week is not None
                else None
            ),
            "experience": self.experience,
            "risk_tolerance": (
                self.risk_tolerance.value if self.risk_tolerance else None
            ),
            "region": self.region.to_dict() if self.region else None,
            "business_stage": self.business_stage,
            "logistics_capacity": self.logistics_capacity,
            "storage_space": self.storage_space,
            "resources": [item.to_dict() for item in self.resources],
            "capabilities": [item.to_dict() for item in self.capabilities],
            "constraints": [item.to_dict() for item in self.constraints],
            "preferences": [item.to_dict() for item in self.preferences],
            "captured_at": self.captured_at.isoformat(),
            "version": self.version,
        }
