"""Capa de aplicación independiente de cualquier interfaz de usuario.

Las exportaciones se resuelven de forma perezosa para que servicios acotados
puedan importar un submódulo sin cargar todo el legado Amazon.
"""

from importlib import import_module

__all__ = [
    "analizar",
    "CONFIGURACION_PREDETERMINADA",
    "crear_dashboard",
    "generar_decision",
    "generar_decision_dominio",
    "exportar",
    "importar_desde_contenido",
    "importar_desde_ruta",
    "generar_insights",
    "puntuar_oportunidades",
    "puntuar_producto",
    "generar_reporte_comercial",
    "LIMITACIONES_PILOTO",
    "PLANTILLA_CLIENTE_CSV",
    "resumir",
    "crear_catalogo_marketplace",
    "comparar_modelos_operativos",
]


_EXPORTS = {
    "analizar": ("application.analysis_service", "analizar"),
    "CONFIGURACION_PREDETERMINADA": ("application.analysis_service", "CONFIGURACION_PREDETERMINADA"),
    "crear_dashboard": ("application.dashboard_service", "crear_dashboard"),
    "generar_decision": ("application.decision_service", "generar_decision"),
    "generar_decision_dominio": ("application.decision_service", "generar_decision_dominio"),
    "exportar": ("application.export_service", "exportar"),
    "importar_desde_contenido": ("application.import_service", "importar_desde_contenido"),
    "importar_desde_ruta": ("application.import_service", "importar_desde_ruta"),
    "generar_insights": ("application.insight_service", "generar_insights"),
    "puntuar_oportunidades": ("application.opportunity_service", "puntuar_oportunidades"),
    "puntuar_producto": ("application.opportunity_service", "puntuar_producto"),
    "LIMITACIONES_PILOTO": ("application.pilot_service", "LIMITACIONES_PILOTO"),
    "PLANTILLA_CLIENTE_CSV": ("application.pilot_service", "PLANTILLA_CLIENTE_CSV"),
    "generar_reporte_comercial": ("application.pilot_service", "generar_reporte_comercial"),
    "crear_catalogo_marketplace": ("application.marketplace_service", "crear_catalogo_marketplace"),
    "comparar_modelos_operativos": ("application.business_model_service", "comparar_modelos_operativos"),
    "resumir": ("application.summary_service", "resumir"),
}


def __getattr__(name):
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as error:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from error
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
