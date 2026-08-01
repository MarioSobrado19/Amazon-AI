"""Puntuación explicable de oportunidades usando métricas ya calculadas."""

import math

from application.errors import ErrorAplicacion, resultado_exitoso, resultado_fallido


PESO_ROI = 40.0
PESO_MARGEN = 30.0
PESO_GANANCIA = 30.0
ROI_REFERENCIA = 200.0
MARGEN_REFERENCIA = 50.0
GANANCIA_REFERENCIA = 30.0

PUNTAJE_EXCEPCIONAL = 85.0
PUNTAJE_MUY_PROMETEDORA = 70.0
PUNTAJE_INTERESANTE = 55.0
PUNTAJE_ANALIZAR_CON_CUIDADO = 35.0


def _es_numero_valido(valor):
    return (
        not isinstance(valor, bool)
        and isinstance(valor, (int, float))
        and math.isfinite(valor)
    )


def _contribucion(valor, referencia, peso):
    proporcion = max(0.0, min(float(valor) / referencia, 1.0))
    return round(proporcion * peso, 1)


def categorizar_oportunidad(puntaje):
    if puntaje >= PUNTAJE_EXCEPCIONAL:
        return "Excepcional"
    if puntaje >= PUNTAJE_MUY_PROMETEDORA:
        return "Muy prometedora"
    if puntaje >= PUNTAJE_INTERESANTE:
        return "Interesante"
    if puntaje >= PUNTAJE_ANALIZAR_CON_CUIDADO:
        return "Analizar con cuidado"
    return "No prioritaria"


def puntuar_producto(producto):
    """Agrega score y explicación sin modificar el producto recibido."""
    if not isinstance(producto, dict):
        return resultado_fallido(
            ErrorAplicacion(
                codigo="producto_invalido",
                mensaje="El producto debe proporcionarse como un conjunto de valores.",
                campo="producto",
            )
        )

    campos = ("roi", "margen", "ganancia")
    for campo in campos:
        if campo not in producto or not _es_numero_valido(producto[campo]):
            return resultado_fallido(
                ErrorAplicacion(
                    codigo="metrica_invalida",
                    mensaje=f"La métrica {campo} debe ser un número válido.",
                    campo=campo,
                )
            )

    puntos_roi = _contribucion(producto["roi"], ROI_REFERENCIA, PESO_ROI)
    puntos_margen = _contribucion(
        producto["margen"], MARGEN_REFERENCIA, PESO_MARGEN
    )
    puntos_ganancia = _contribucion(
        producto["ganancia"], GANANCIA_REFERENCIA, PESO_GANANCIA
    )
    puntaje = round(puntos_roi + puntos_margen + puntos_ganancia, 1)

    puntuado = dict(producto)
    puntuado["opportunity_score"] = puntaje
    puntuado["opportunity_category"] = categorizar_oportunidad(puntaje)
    puntuado["opportunity_factors"] = {
        "roi": {
            "valor": producto["roi"],
            "puntos": puntos_roi,
            "maximo": PESO_ROI,
            "referencia": ROI_REFERENCIA,
        },
        "margen": {
            "valor": producto["margen"],
            "puntos": puntos_margen,
            "maximo": PESO_MARGEN,
            "referencia": MARGEN_REFERENCIA,
        },
        "ganancia": {
            "valor": producto["ganancia"],
            "puntos": puntos_ganancia,
            "maximo": PESO_GANANCIA,
            "referencia": GANANCIA_REFERENCIA,
        },
    }
    return resultado_exitoso(puntuado)


def puntuar_oportunidades(productos):
    if not isinstance(productos, list):
        return resultado_fallido(
            ErrorAplicacion(
                codigo="productos_invalidos",
                mensaje="Los productos deben proporcionarse como una lista.",
                campo="productos",
            )
        )

    resultados = []
    for posicion, producto in enumerate(productos, start=1):
        puntuacion = puntuar_producto(producto)
        if not puntuacion["exito"]:
            errores = []
            for error in puntuacion["errores"]:
                error_con_posicion = dict(error)
                error_con_posicion["fila"] = posicion
                errores.append(error_con_posicion)
            return resultado_fallido(errores)
        resultados.append(puntuacion["datos"])

    return resultado_exitoso(resultados)
