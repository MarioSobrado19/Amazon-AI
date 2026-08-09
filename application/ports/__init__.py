"""Puertos de entrada para infraestructura externa futura."""

from application.ports.marketplace_adapter import (
    MarketplaceAdapter,
    MarketplaceAdapterError,
    MarketplaceAdapterTimeout,
    MarketplaceAdapterUnavailable,
)

__all__ = [
    "MarketplaceAdapter",
    "MarketplaceAdapterError",
    "MarketplaceAdapterTimeout",
    "MarketplaceAdapterUnavailable",
]
