from dataclasses import dataclass
from datetime import datetime

from domain.entities._marketplace_validation import (
    currency_code,
    required_text,
    text_tuple,
    valid_period,
)
from domain.entities._identity import internal_id
from domain.enums import ConfidenceLevel
from domain.exceptions import DomainValidationError
from domain.value_objects import Region


@dataclass(frozen=True, slots=True, eq=False)
class Marketplace:
    """Canal genérico con UUID interno separado de futuros IDs externos."""

    marketplace_id: str
    name: str
    region: Region
    currency: str
    source: str
    valid_from: datetime
    version: str
    categories: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    general_requirements: tuple[str, ...] = ()
    general_restrictions: tuple[str, ...] = ()
    valid_until: datetime | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    def __post_init__(self):
        object.__setattr__(
            self, "marketplace_id", internal_id(self.marketplace_id, "marketplace_id")
        )
        object.__setattr__(self, "name", required_text(self.name, "name"))
        if not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser una Region válida.")
        object.__setattr__(self, "currency", currency_code(self.currency))
        object.__setattr__(self, "source", required_text(self.source, "source"))
        object.__setattr__(self, "version", required_text(self.version, "version"))
        for field_name in (
            "categories",
            "capabilities",
            "general_requirements",
            "general_restrictions",
        ):
            object.__setattr__(self, field_name, text_tuple(getattr(self, field_name), field_name))
        valid_from, valid_until = valid_period(self.valid_from, self.valid_until)
        if valid_from is None:
            raise DomainValidationError("valid_from es obligatorio.")
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "valid_until", valid_until)
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser un nivel válido.")

    def __eq__(self, other):
        if not isinstance(other, Marketplace):
            return NotImplemented
        return self.marketplace_id == other.marketplace_id

    def __hash__(self):
        return hash(self.marketplace_id)

    def to_dict(self):
        return {
            "marketplace_id": self.marketplace_id,
            "name": self.name,
            "region": self.region.to_dict(),
            "currency": self.currency,
            "categories": list(self.categories),
            "capabilities": list(self.capabilities),
            "general_requirements": list(self.general_requirements),
            "general_restrictions": list(self.general_restrictions),
            "source": self.source,
            "valid_from": self.valid_from.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "confidence": self.confidence.value,
            "version": self.version,
        }
