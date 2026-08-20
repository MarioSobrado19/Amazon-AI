"""Puertos de entrada para infraestructura externa futura."""

from application.ports.marketplace_adapter import (
    MarketplaceAdapter,
    MarketplaceAdapterError,
    MarketplaceAdapterTimeout,
    MarketplaceAdapterUnavailable,
)
from application.ports.research_capability import ResearchCapability
from application.ports.discovery_source import DiscoverySource

__all__ = [
    "MarketplaceAdapter",
    "MarketplaceAdapterError",
    "MarketplaceAdapterTimeout",
    "MarketplaceAdapterUnavailable",
    "ResearchCapability",
    "DiscoverySource",
]
