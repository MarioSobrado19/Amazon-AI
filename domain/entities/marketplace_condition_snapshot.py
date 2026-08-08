from dataclasses import dataclass
from datetime import datetime

from domain.entities._marketplace_validation import (
    aware_datetime,
    optional_aware_datetime,
    required_text,
)
from domain.entities._identity import internal_id
from domain.entities.marketplace import Marketplace
from domain.enums import ConfidenceLevel, FreshnessStatus, VerificationStatus
from domain.exceptions import DomainValidationError
from domain.value_objects import FrozenMapping, Region


@dataclass(frozen=True, slots=True, eq=False)
class MarketplaceConditionSnapshot:
    """Captura histórica inmutable con identidad interna propia y trazable."""

    snapshot_id: str
    marketplace: Marketplace
    region: Region
    condition_type: str
    values: FrozenMapping
    source: str
    consulted_at: datetime
    effective_at: datetime
    freshness: FreshnessStatus
    confidence: ConfidenceLevel
    verification_status: VerificationStatus
    version: str
    expires_at: datetime | None = None

    def __post_init__(self):
        object.__setattr__(self, "snapshot_id", internal_id(self.snapshot_id, "snapshot_id"))
        if not isinstance(self.marketplace, Marketplace):
            raise DomainValidationError("marketplace debe ser un Marketplace válido.")
        if not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser una Region válida.")
        if self.region.country_code != self.marketplace.region.country_code:
            raise DomainValidationError("region debe pertenecer al país del marketplace.")
        object.__setattr__(
            self, "condition_type", required_text(self.condition_type, "condition_type")
        )
        if not isinstance(self.values, FrozenMapping):
            object.__setattr__(self, "values", FrozenMapping.from_mapping(self.values))
        object.__setattr__(self, "source", required_text(self.source, "source"))
        object.__setattr__(
            self, "consulted_at", aware_datetime(self.consulted_at, "consulted_at")
        )
        object.__setattr__(
            self, "effective_at", aware_datetime(self.effective_at, "effective_at")
        )
        expires_at = optional_aware_datetime(self.expires_at, "expires_at")
        if expires_at is not None and expires_at < self.effective_at:
            raise DomainValidationError("expires_at no puede ser anterior a effective_at.")
        object.__setattr__(self, "expires_at", expires_at)
        if not isinstance(self.freshness, FreshnessStatus):
            raise DomainValidationError("freshness debe ser válido.")
        if not isinstance(self.confidence, ConfidenceLevel):
            raise DomainValidationError("confidence debe ser válido.")
        if not isinstance(self.verification_status, VerificationStatus):
            raise DomainValidationError("verification_status debe ser válido.")
        object.__setattr__(self, "version", required_text(self.version, "version"))

    def __eq__(self, other):
        if not isinstance(other, MarketplaceConditionSnapshot):
            return NotImplemented
        return self.snapshot_id == other.snapshot_id

    def __hash__(self):
        return hash(self.snapshot_id)

    def to_dict(self):
        return {
            "snapshot_id": self.snapshot_id,
            "marketplace": self.marketplace.to_dict(),
            "region": self.region.to_dict(),
            "condition_type": self.condition_type,
            "values": self.values.to_dict(),
            "source": self.source,
            "consulted_at": self.consulted_at.isoformat(),
            "effective_at": self.effective_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "freshness": self.freshness.value,
            "confidence": self.confidence.value,
            "verification_status": self.verification_status.value,
            "version": self.version,
        }
