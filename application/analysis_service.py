"""Coordinación del motor de análisis sin dependencias de interfaz."""

from application.errors import ErrorAplicacion, resultado_exitoso, resultado_fallido
from scout import analizar_productos


FILTROS_PERMITIDOS = {
    "roi_minimo",
    "margen_minimo",
    "ganancia_minima",
    "precio_maximo",
    "texto_nombre",
}


def analizar(productos, filtros=None):
    if not isinstance(productos, list) or not productos:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="productos_invalidos",
                mensaje="Carga al menos un producto válido antes de analizar.",
                campo="productos",
            )
        )

    if filtros is None:
        filtros = {}
    elif not isinstance(filtros, dict):
        return resultado_fallido(
            ErrorAplicacion(
                codigo="filtros_invalidos",
                mensaje="Los filtros deben proporcionarse como un conjunto de criterios.",
                campo="filtros",
            )
        )

    desconocidos = sorted(set(filtros) - FILTROS_PERMITIDOS)
    if desconocidos:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="filtros_desconocidos",
                mensaje=f"Filtros no reconocidos: {', '.join(desconocidos)}.",
                campo="filtros",
            )
        )

    try:
        resultados = analizar_productos(productos, **filtros)
    except Exception:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="analisis_fallido",
                mensaje=(
                    "No se pudieron analizar los productos. "
                    "Revisa los datos e inténtalo nuevamente."
                ),
            )
        )

    advertencias = []
    if not resultados:
        advertencias.append(
            "Ningún producto cumple los filtros activos; prueba criterios menos restrictivos."
        )

    return resultado_exitoso(
        {
            "resultados": resultados,
            "total_analizado": len(productos),
            "total_mostrado": len(resultados),
            "filtros_aplicados": dict(filtros),
        },
        advertencias=advertencias,
    )
