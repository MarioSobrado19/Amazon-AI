"""Caso de uso seguro para analizar una oportunidad observada en eBay.

La capa de aplicación valida entradas, ejecuta el pipeline existente y devuelve
un contrato estable para la UI. No calcula fórmulas financieras ni interpreta
listings activos como ventas o demanda.
"""

import math
import os
import re

from application.ebay_production_pipeline import run_ebay_production_pipeline
from application.resale_economics import EbayFeeAssumptions
from infrastructure.oauth_client import ApiError


def estado_conexion_ebay(environ=None):
    """Describe disponibilidad sin devolver credenciales ni sus valores."""
    environ = os.environ if environ is None else environ
    environment = environ.get("EBAY_ENVIRONMENT", "sandbox").strip().lower()
    configured = bool(
        environ.get("EBAY_CLIENT_ID") and environ.get("EBAY_CLIENT_SECRET")
    )
    production_approved = (
        environ.get("EBAY_BUY_PRODUCTION_APPROVED", "false").strip().lower()
        == "true"
    )
    ready = configured and environment == "production" and production_approved
    return {
        "ready": ready,
        "environment": environment,
        "credentials_configured": configured,
        "production_approved": production_approved,
    }


def _numero(valor, propiedad, *, minimo=0.0, maximo=None, estricto=False):
    if isinstance(valor, bool):
        raise ValueError(f"{propiedad} debe ser un número válido.")
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{propiedad} debe ser un número válido.") from None
    if not math.isfinite(numero):
        raise ValueError(f"{propiedad} debe ser un número finito.")
    if (estricto and numero <= minimo) or (not estricto and numero < minimo):
        comparacion = "mayor que" if estricto else "igual o mayor que"
        raise ValueError(f"{propiedad} debe ser {comparacion} {minimo:g}.")
    if maximo is not None and numero > maximo:
        raise ValueError(f"{propiedad} no puede superar {maximo:g}.")
    return numero


def analizar_oportunidad_controlada(
    *,
    gtin,
    costo_manual,
    tarifa_porcentaje,
    tarifa_fija=0.40,
    envio=0.0,
    impuesto_compra=0.0,
    empaque=0.0,
    promocion_porcentaje=0.0,
    otros=0.0,
    fuente=None,
):
    """Ejecuta la observación y valoración sin convertirla en recomendación."""
    gtin_normalizado = re.sub(r"\D", "", str(gtin or ""))
    if len(gtin_normalizado) not in {8, 12, 13, 14}:
        return {
            "exito": False,
            "datos": None,
            "errores": [{
                "codigo": "gtin_invalido",
                "mensaje": "Escribe un GTIN, UPC o EAN válido de 8, 12, 13 o 14 dígitos.",
            }],
            "advertencias": [],
        }

    try:
        assumptions = EbayFeeAssumptions(
            percentage=_numero(tarifa_porcentaje, "La tarifa porcentual", maximo=100) / 100,
            fixed=_numero(tarifa_fija, "La tarifa fija"),
            shipping=_numero(envio, "El envío"),
            acquisition_sales_tax=_numero(impuesto_compra, "El impuesto de compra"),
            packaging=_numero(empaque, "El empaque"),
            promotion_percentage=_numero(
                promocion_porcentaje, "La promoción porcentual", maximo=100
            ) / 100,
            other=_numero(otros, "Los otros costos"),
        )
        result = run_ebay_production_pipeline(
            gtin=gtin_normalizado,
            manual_cost=_numero(
                costo_manual, "El costo de compra", minimo=0, estricto=True
            ),
            fee_assumptions=assumptions,
            source=fuente,
        )
    except ApiError as error:
        messages = {
            "authentication_failed": "eBay rechazó la autenticación. Revisa la configuración local.",
            "rate_limited": "eBay alcanzó temporalmente su límite de consultas. Intenta más tarde.",
            "network_error": "No fue posible conectar con eBay. Revisa la conexión e intenta nuevamente.",
        }
        return {
            "exito": False,
            "datos": None,
            "errores": [{
                "codigo": error.code,
                "mensaje": messages.get(
                    error.code,
                    "eBay no pudo completar la consulta en este momento.",
                ),
                "reintentable": error.retryable,
            }],
            "advertencias": [],
        }
    except (TypeError, ValueError) as error:
        return {
            "exito": False,
            "datos": None,
            "errores": [{"codigo": "entrada_invalida", "mensaje": str(error)}],
            "advertencias": [],
        }
    except Exception:
        # La UI no debe revelar payloads, headers, tokens ni detalles internos.
        return {
            "exito": False,
            "datos": None,
            "errores": [{
                "codigo": "error_interno",
                "mensaje": "No fue posible completar el análisis. Intenta nuevamente.",
            }],
            "advertencias": [],
        }

    warnings = list(result.get("valuation", {}).get("limitations") or [])
    warnings.append(
        "Los listings activos no demuestran ventas, demanda ni rentabilidad futura."
    )
    return {
        "exito": True,
        "datos": result,
        "errores": [],
        "advertencias": warnings,
    }
