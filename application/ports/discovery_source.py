"""Puerto de fuentes de discovery; no contiene reglas de proveedores."""

from typing import Protocol

from application.discovery_models import DiscoveryRequest, DiscoverySourceResult


class DiscoverySource(Protocol):
    source_id: str

    def collect(self, request: DiscoveryRequest) -> DiscoverySourceResult:
        """Obtiene señales tipadas o un estado explícito NO_DATA/failure."""


__all__ = ["DiscoverySource"]
