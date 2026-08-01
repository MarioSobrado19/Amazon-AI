"""Coordinación del motor de análisis sin dependencias de interfaz."""

from application.errors import ErrorAplicacion, resultado_exitoso, resultado_fallido
from config import (
    ANALISIS,
    ENVIO_PREDETERMINADO,
    OTROS_COSTOS_PREDETERMINADOS,
    TARIFA_AMAZON_PORCENTAJE,
)
from filters import filtrar_productos
from scout import analizar_productos


FILTROS_PERMITIDOS = {
    "roi_minimo",
    "margen_minimo",
    "ganancia_minima",
    "precio_maximo",
    "texto_nombre",
}

CONFIGURACION_PREDETERMINADA = {
    "envio_predeterminado": ENVIO_PREDETERMINADO,
    "tarifa_amazon_porcentaje": TARIFA_AMAZON_PORCENTAJE,
    "otros_costos_predeterminados": OTROS_COSTOS_PREDETERMINADOS,
    "roi_excelente": ANALISIS["roi_excelente"],
    "roi_bueno": ANALISIS["roi_bueno"],
    "roi_regular": ANALISIS["roi_regular"],
}


def _preparar_configuracion(configuracion):
    if configuracion is None:
        return CONFIGURACION_PREDETERMINADA.copy(), None
    if not isinstance(configuracion, dict):
        return None, ErrorAplicacion(
            codigo="configuracion_invalida",
            mensaje="La configuración debe proporcionarse como un conjunto de valores.",
            campo="configuracion",
        )

    desconocidos = sorted(set(configuracion) - set(CONFIGURACION_PREDETERMINADA))
    if desconocidos:
        return None, ErrorAplicacion(
            codigo="configuracion_desconocida",
            mensaje=f"Valores de configuración no reconocidos: {', '.join(desconocidos)}.",
            campo="configuracion",
        )

    valores = CONFIGURACION_PREDETERMINADA | configuracion
    for nombre, valor in valores.items():
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return None, ErrorAplicacion(
                codigo="configuracion_invalida",
                mensaje=f"El valor de {nombre} debe ser numérico.",
                campo=nombre,
            )
        if valor < 0:
            return None, ErrorAplicacion(
                codigo="configuracion_invalida",
                mensaje=f"El valor de {nombre} no puede ser negativo.",
                campo=nombre,
            )

    if valores["tarifa_amazon_porcentaje"] > 1:
        return None, ErrorAplicacion(
            codigo="configuracion_invalida",
            mensaje="La tarifa de Amazon debe estar entre 0 % y 100 %.",
            campo="tarifa_amazon_porcentaje",
        )
    if not (
        valores["roi_excelente"]
        >= valores["roi_bueno"]
        >= valores["roi_regular"]
    ):
        return None, ErrorAplicacion(
            codigo="configuracion_invalida",
            mensaje="Los niveles de ROI deben estar ordenados de mayor a menor.",
            campo="niveles_roi",
        )

    return {nombre: float(valor) for nombre, valor in valores.items()}, None


def analizar(productos, filtros=None, configuracion=None):
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

    configuracion_aplicada, error_configuracion = _preparar_configuracion(
        configuracion
    )
    if error_configuracion:
        return resultado_fallido(error_configuracion)

    try:
        resultados_completos = analizar_productos(
            productos,
            **configuracion_aplicada,
        )
        resultados = filtrar_productos(resultados_completos, **filtros)
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
            "resultados_completos": resultados_completos,
            "total_analizado": len(productos),
            "total_mostrado": len(resultados),
            "filtros_aplicados": dict(filtros),
            "configuracion_aplicada": configuracion_aplicada,
        },
        advertencias=advertencias,
    )
