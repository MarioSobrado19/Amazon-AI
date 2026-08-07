"""Adaptadores internos entre contratos heredados y el dominio oficial."""

from application.adapters.opportunity_domain_adapter import (
    construir_oportunidad_desde_formato_actual,
    convertir_oportunidad_a_formato_actual,
)

__all__ = [
    "construir_oportunidad_desde_formato_actual",
    "convertir_oportunidad_a_formato_actual",
]
