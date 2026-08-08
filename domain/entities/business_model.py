from dataclasses import dataclass
from datetime import datetime

from domain.entities._marketplace_validation import (
    optional_text,
    required_text,
    text_tuple,
    valid_period,
)
from domain.entities._identity import internal_id
from domain.enums import ConfidenceLevel, OperationalLoad
from domain.exceptions import DomainValidationError
from domain.value_objects import Region


@dataclass(frozen=True, slots=True, eq=False)
class BusinessModel:
    """Forma operativa genérica con UUID interno independiente de IDs externos."""

    business_model_id: str
    name: str
    region: Region
    confidence: ConfidenceLevel
    version: str
    description: str | None = None
    marketplace_id: str | None = None
    seller_responsibilities: tuple[str, ...] = ()
    marketplace_responsibilities: tuple[str, ...] = ()
    fulfillment: str | None = None
    storage: str | None = None
    shipping: str | None = None
    returns: str | None = None
    customer_service: str | None = None
    requirements: tuple[str, ...] = ()
    restrictions: tuple[str, ...] = ()
    advantages: tuple[str, ...] = ()
    disadvantages: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    scalability: str | None = None
    operational_load: OperationalLoad = OperationalLoad.VARIABLE
    recommended_experience: str | None = None
    source: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    represents_external_conditions: bool = False

    def __post_init__(self):
        object.__setattr__(
            self,
            "business_model_id",
            internal_id(self.business_model_id, "business_model_id"),
        )
        object.__setattr__(self, "name", required_text(self.name, "name"))
        if not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser una Region válida.")
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser un nivel válido.")
        object.__setattr__(self, "version", required_text(self.version, "version"))
        object.__setattr__(self, "description", optional_text(self.description, "description"))
        object.__setattr__(
            self,
            "marketplace_id",
            internal_id(self.marketplace_id, "marketplace_id")
            if self.marketplace_id is not None
            else None,
        )
        for field_name in (
            "seller_responsibilities",
            "marketplace_responsibilities",
            "requirements",
            "restrictions",
            "advantages",
            "disadvantages",
            "risks",
        ):
            object.__setattr__(self, field_name, text_tuple(getattr(self, field_name), field_name))
        for field_name in (
            "fulfillment",
            "storage",
            "shipping",
            "returns",
            "customer_service",
            "scalability",
            "recommended_experience",
            "source",
        ):
            object.__setattr__(self, field_name, optional_text(getattr(self, field_name), field_name))
        if not isinstance(self.operational_load, OperationalLoad):
            raise DomainValidationError("operational_load debe ser válido.")
        if not isinstance(self.represents_external_conditions, bool):
            raise DomainValidationError("represents_external_conditions debe ser booleano.")
        valid_from, valid_until = valid_period(self.valid_from, self.valid_until)
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "valid_until", valid_until)

        has_external_conditions = bool(
            self.represents_external_conditions
            or self.requirements
            or self.restrictions
            or self.source
            or self.valid_from
            or self.valid_until
        )
        if has_external_conditions and (self.source is None or self.valid_from is None):
            raise DomainValidationError(
                "Las condiciones externas requieren source y valid_from."
            )

    def __eq__(self, other):
        if not isinstance(other, BusinessModel):
            return NotImplemented
        return self.business_model_id == other.business_model_id

    def __hash__(self):
        return hash(self.business_model_id)

    def to_dict(self):
        return {
            "business_model_id": self.business_model_id,
            "name": self.name,
            "description": self.description,
            "marketplace_id": self.marketplace_id,
            "region": self.region.to_dict(),
            "seller_responsibilities": list(self.seller_responsibilities),
            "marketplace_responsibilities": list(self.marketplace_responsibilities),
            "fulfillment": self.fulfillment,
            "storage": self.storage,
            "shipping": self.shipping,
            "returns": self.returns,
            "customer_service": self.customer_service,
            "requirements": list(self.requirements),
            "restrictions": list(self.restrictions),
            "advantages": list(self.advantages),
            "disadvantages": list(self.disadvantages),
            "risks": list(self.risks),
            "scalability": self.scalability,
            "operational_load": self.operational_load.value,
            "recommended_experience": self.recommended_experience,
            "source": self.source,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "confidence": self.confidence.value,
            "version": self.version,
            "represents_external_conditions": self.represents_external_conditions,
        }
