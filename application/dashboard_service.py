"""Resumen del dashboard a partir de resultados previamente calculados."""

from application.errors import ErrorAplicacion, resultado_fallido
from application.summary_service import resumir


def crear_dashboard(resultados, total_analizado=None):
    """Construye indicadores y la oportunidad principal sin recalcular métricas."""
    resumen = resumir(resultados, total_analizado)
    if not resumen["exito"]:
        return resumen

    destacado = None
    if resultados:
        try:
            destacado = max(resultados, key=lambda producto: producto["roi"])
            campos_requeridos = (
                "nombre",
                "roi",
                "ganancia",
                "margen",
                "evaluacion",
            )
            if not isinstance(destacado, dict) or any(
                campo not in destacado for campo in campos_requeridos
            ):
                raise KeyError("producto_destacado")
        except (KeyError, TypeError):
            return resultado_fallido(
                ErrorAplicacion(
                    codigo="resultados_invalidos",
                    mensaje=(
                        "No se pudo crear el dashboard porque los resultados "
                        "están incompletos."
                    ),
                    campo="resultados",
                )
            )

    datos = dict(resumen["datos"])
    datos["producto_destacado"] = dict(destacado) if destacado else None
    resumen["datos"] = datos
    return resumen
