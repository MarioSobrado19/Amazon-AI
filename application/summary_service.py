"""Creación de indicadores generales a partir de resultados ya calculados."""

from application.errors import ErrorAplicacion, resultado_exitoso, resultado_fallido


def resumir(resultados, total_analizado=None):
    if not isinstance(resultados, list):
        return resultado_fallido(
            ErrorAplicacion(
                codigo="resultados_invalidos",
                mensaje="Los resultados deben proporcionarse como una lista.",
                campo="resultados",
            )
        )

    if total_analizado is None:
        total_analizado = len(resultados)
    elif (
        isinstance(total_analizado, bool)
        or not isinstance(total_analizado, int)
        or total_analizado < len(resultados)
    ):
        return resultado_fallido(
            ErrorAplicacion(
                codigo="total_analizado_invalido",
                mensaje=(
                    "El total analizado debe ser un entero no negativo y no puede "
                    "ser menor que la cantidad de resultados."
                ),
                campo="total_analizado",
            )
        )

    clasificaciones = {
        "EXCELENTE PRODUCTO": 0,
        "BUEN PRODUCTO": 0,
        "REGULAR": 0,
        "NO RECOMENDADO": 0,
    }

    try:
        for producto in resultados:
            evaluacion = producto.get("evaluacion")
            if evaluacion in clasificaciones:
                clasificaciones[evaluacion] += 1

        mejor = max(resultados, key=lambda producto: producto["roi"], default=None)
        mayor_ganancia = max(
            resultados,
            key=lambda producto: producto["ganancia"],
            default=None,
        )
    except (AttributeError, KeyError, TypeError):
        return resultado_fallido(
            ErrorAplicacion(
                codigo="resultados_invalidos",
                mensaje=(
                    "No se pudo crear el resumen porque los resultados "
                    "están incompletos."
                ),
                campo="resultados",
            )
        )

    return resultado_exitoso(
        {
            "total_analizado": total_analizado,
            "total_mostrado": len(resultados),
            "mejor_roi": mejor["roi"] if mejor else None,
            "producto_mejor_roi": mejor["nombre"] if mejor else None,
            "mayor_ganancia": mayor_ganancia["ganancia"] if mayor_ganancia else None,
            "producto_mayor_ganancia": (
                mayor_ganancia["nombre"] if mayor_ganancia else None
            ),
            "cantidad_excelentes": clasificaciones["EXCELENTE PRODUCTO"],
            "cantidad_buenos": clasificaciones["BUEN PRODUCTO"],
            "cantidad_regulares": clasificaciones["REGULAR"],
            "cantidad_no_recomendados": clasificaciones["NO RECOMENDADO"],
        }
    )
