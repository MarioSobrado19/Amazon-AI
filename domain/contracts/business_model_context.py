from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from domain.entities._marketplace_validation import optional_text, text_tuple
from domain.enums import RiskLevel
from domain.exceptions import DomainValidationError
from domain.value_objects import Money, Region


EXPERIENCE_LEVELS = {"principiante", "intermedio", "avanzado"}
CAPACITY_LEVELS = {"ninguna", "baja", "media", "alta"}
STORAGE_LEVELS = {"ninguno", "limitado", "moderado", "amplio"}
CONTROL_LEVELS = {"bajo", "medio", "alto"}


def _choice(value, field, choices):
    value = optional_text(value, field)
    if value is not None and value not in choices:
        raise DomainValidationError(f"{field} no es válido.")
    return value


def _optional_non_negative_decimal(value, field):
    if value is None:
        return None
    if isinstance(value, bool):
        raise DomainValidationError(f"{field} debe ser numérico y no negativo.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise DomainValidationError(
            f"{field} debe ser numérico y no negativo."
        ) from error
    if not number.is_finite() or number < 0:
        raise DomainValidationError(f"{field} debe ser numérico y no negativo.")
    return number


@dataclass(frozen=True, slots=True)
class BusinessModelContext:
    """Contexto opcional, inmutable y explícito para comparar modelos."""

    budget: Money | None = None
    experience: str | None = None
    available_time_hours: Decimal | None = None
    objective: str | None = None
    risk_tolerance: RiskLevel | None = None
    region: Region | None = None
    logistics_capacity: str | None = None
    storage_space: str | None = None
    operational_control_preference: str | None = None
    business_stage: str | None = None
    declared_restrictions: tuple[str, ...] = ()

    def __post_init__(self):
        if self.budget is not None:
            if not isinstance(self.budget, Money) or self.budget.amount < 0:
                raise DomainValidationError("budget debe ser Money no negativo.")
        object.__setattr__(
            self, "experience", _choice(self.experience, "experience", EXPERIENCE_LEVELS)
        )
        object.__setattr__(
            self,
            "available_time_hours",
            _optional_non_negative_decimal(
                self.available_time_hours, "available_time_hours"
            ),
        )
        object.__setattr__(self, "objective", optional_text(self.objective, "objective"))
        if self.risk_tolerance is not None and not isinstance(
            self.risk_tolerance, RiskLevel
        ):
            raise DomainValidationError("risk_tolerance debe ser RiskLevel válido.")
        if self.region is not None and not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser Region válida.")
        object.__setattr__(
            self,
            "logistics_capacity",
            _choice(self.logistics_capacity, "logistics_capacity", CAPACITY_LEVELS),
        )
        object.__setattr__(
            self,
            "storage_space",
            _choice(self.storage_space, "storage_space", STORAGE_LEVELS),
        )
        object.__setattr__(
            self,
            "operational_control_preference",
            _choice(
                self.operational_control_preference,
                "operational_control_preference",
                CONTROL_LEVELS,
            ),
        )
        object.__setattr__(
            self,
            "business_stage",
            optional_text(self.business_stage, "business_stage"),
        )
        object.__setattr__(
            self,
            "declared_restrictions",
            text_tuple(self.declared_restrictions, "declared_restrictions"),
        )

    @property
    def is_beginner(self):
        return self.experience == "principiante"

    def missing_fields(self):
        fields = (
            "budget",
            "experience",
            "available_time_hours",
            "objective",
            "risk_tolerance",
            "region",
            "logistics_capacity",
            "storage_space",
            "operational_control_preference",
            "business_stage",
        )
        return tuple(field for field in fields if getattr(self, field) is None)

    def to_dict(self):
        return {
            "budget": self.budget.to_dict() if self.budget else None,
            "experience": self.experience,
            "available_time_hours": (
                str(self.available_time_hours)
                if self.available_time_hours is not None
                else None
            ),
            "objective": self.objective,
            "risk_tolerance": self.risk_tolerance.value if self.risk_tolerance else None,
            "region": self.region.to_dict() if self.region else None,
            "logistics_capacity": self.logistics_capacity,
            "storage_space": self.storage_space,
            "operational_control_preference": self.operational_control_preference,
            "business_stage": self.business_stage,
            "declared_restrictions": list(self.declared_restrictions),
        }
