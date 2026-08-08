from dataclasses import dataclass
from datetime import datetime

from domain.entities import BusinessModel, Marketplace, MarketplaceConditionSnapshot
from domain.entities._marketplace_validation import aware_datetime, required_text, text_tuple
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class MarketplaceCatalogResult:
    """Catálogo versionado de opciones genéricas disponibles en un contexto."""

    catalog_id: str
    version: str
    generated_at: datetime
    marketplaces: tuple[Marketplace, ...] = ()
    business_models: tuple[BusinessModel, ...] = ()
    snapshots: tuple[MarketplaceConditionSnapshot, ...] = ()
    unavailable_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "catalog_id", required_text(self.catalog_id, "catalog_id"))
        object.__setattr__(self, "version", required_text(self.version, "version"))
        object.__setattr__(
            self, "generated_at", aware_datetime(self.generated_at, "generated_at")
        )
        for field_name, expected_type in (
            ("marketplaces", Marketplace),
            ("business_models", BusinessModel),
            ("snapshots", MarketplaceConditionSnapshot),
        ):
            values = tuple(getattr(self, field_name))
            if any(not isinstance(item, expected_type) for item in values):
                raise DomainValidationError(f"{field_name} contiene valores inválidos.")
            object.__setattr__(self, field_name, values)
        object.__setattr__(
            self, "unavailable_reasons", text_tuple(self.unavailable_reasons, "unavailable_reasons")
        )
        object.__setattr__(self, "warnings", text_tuple(self.warnings, "warnings"))

    def to_dict(self):
        return {
            "catalog_id": self.catalog_id,
            "version": self.version,
            "generated_at": self.generated_at.isoformat(),
            "marketplaces": [item.to_dict() for item in self.marketplaces],
            "business_models": [item.to_dict() for item in self.business_models],
            "snapshots": [item.to_dict() for item in self.snapshots],
            "unavailable_reasons": list(self.unavailable_reasons),
            "warnings": list(self.warnings),
        }

