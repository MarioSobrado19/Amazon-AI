from typing import Protocol

from domain.entities import BusinessModel, Marketplace, MarketplaceConditionSnapshot
from domain.value_objects import Region


class MarketplaceAdapterError(Exception):
    """Fallo funcional estable de una fuente externa futura."""

    code = "adapter_error"
    retryable = False


class MarketplaceAdapterUnavailable(MarketplaceAdapterError):
    code = "adapter_unavailable"
    retryable = True


class MarketplaceAdapterTimeout(MarketplaceAdapterError):
    code = "adapter_timeout"
    retryable = True


class MarketplaceAdapter(Protocol):
    """Puerto genérico; no conoce proveedores, programas ni APIs concretas."""

    @property
    def adapter_id(self) -> str:
        """Identificador estable y no secreto del adaptador."""

    def get_marketplace(self, region: Region) -> Marketplace | None:
        """Devuelve la identidad normalizada disponible para la región."""

    def list_business_models(
        self, marketplace: Marketplace, region: Region
    ) -> tuple[BusinessModel, ...]:
        """Lista modelos operativos normalizados, sin evaluarlos."""

    def list_condition_snapshots(
        self, marketplace: Marketplace, region: Region
    ) -> tuple[MarketplaceConditionSnapshot, ...]:
        """Lista condiciones históricas normalizadas, incluidas las expiradas."""

    def list_requirements(
        self, marketplace: Marketplace, region: Region
    ) -> tuple[str, ...]:
        """Lista requisitos conocidos y trazables."""

    def list_restrictions(
        self, marketplace: Marketplace, region: Region
    ) -> tuple[str, ...]:
        """Lista restricciones conocidas y trazables."""

    def list_capabilities(
        self, marketplace: Marketplace, region: Region
    ) -> tuple[str, ...]:
        """Lista capacidades conocidas para el contexto."""


__all__ = [
    "MarketplaceAdapter",
    "MarketplaceAdapterError",
    "MarketplaceAdapterTimeout",
    "MarketplaceAdapterUnavailable",
]
