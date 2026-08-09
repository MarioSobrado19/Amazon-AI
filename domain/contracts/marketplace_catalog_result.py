from dataclasses import dataclass, field
from datetime import datetime

from domain.entities import BusinessModel, Marketplace, MarketplaceConditionSnapshot
from domain.entities._marketplace_validation import aware_datetime, required_text, text_tuple
from domain.contracts.marketplace_catalog_issue import MarketplaceCatalogIssue
from domain.enums import ConfidenceLevel
from domain.exceptions import DomainValidationError
from domain.value_objects import FrozenMapping


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
    requirements: tuple[str, ...] = ()
    restrictions: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    missing_data: tuple[str, ...] = ()
    functional_errors: tuple[MarketplaceCatalogIssue, ...] = ()
    freshness_summary: FrozenMapping = field(default_factory=FrozenMapping)
    sources: tuple[str, ...] = ()
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

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
        for field_name in (
            "unavailable_reasons",
            "warnings",
            "requirements",
            "restrictions",
            "capabilities",
            "missing_data",
            "sources",
        ):
            object.__setattr__(
                self, field_name, text_tuple(getattr(self, field_name), field_name)
            )
        functional_errors = tuple(self.functional_errors)
        if any(not isinstance(item, MarketplaceCatalogIssue) for item in functional_errors):
            raise DomainValidationError(
                "functional_errors debe contener MarketplaceCatalogIssue válidos."
            )
        object.__setattr__(self, "functional_errors", functional_errors)
        if not isinstance(self.freshness_summary, FrozenMapping):
            object.__setattr__(
                self,
                "freshness_summary",
                FrozenMapping.from_mapping(self.freshness_summary),
            )
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser un nivel válido.")

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
            "requirements": list(self.requirements),
            "restrictions": list(self.restrictions),
            "capabilities": list(self.capabilities),
            "missing_data": list(self.missing_data),
            "functional_errors": [item.to_dict() for item in self.functional_errors],
            "freshness_summary": self.freshness_summary.to_dict(),
            "sources": list(self.sources),
            "confidence": self.confidence.value,
        }
