from calculator import calcular_rentabilidad
from config import ANALISIS
from filters import filtrar_productos


def clasificar_producto(
    roi,
    roi_excelente=ANALISIS["roi_excelente"],
    roi_bueno=ANALISIS["roi_bueno"],
    roi_regular=ANALISIS["roi_regular"],
):
    if roi >= roi_excelente:
        return "EXCELENTE PRODUCTO"
    if roi >= roi_bueno:
        return "BUEN PRODUCTO"
    if roi >= roi_regular:
        return "REGULAR"
    return "NO RECOMENDADO"


def analizar_productos(
    productos,
    roi_minimo=None,
    margen_minimo=None,
    ganancia_minima=None,
    precio_maximo=None,
    texto_nombre=None,
):
    resultados = []

    for producto in productos:
        resultado = calcular_rentabilidad(
            producto["nombre"],
            producto["costo"],
            producto["precio"],
        )
        resultado["evaluacion"] = clasificar_producto(resultado["roi"])
        resultados.append(resultado)

    resultados_ordenados = sorted(
        resultados,
        key=lambda producto: producto["roi"],
        reverse=True,
    )

    return filtrar_productos(
        resultados_ordenados,
        roi_minimo=roi_minimo,
        margen_minimo=margen_minimo,
        ganancia_minima=ganancia_minima,
        precio_maximo=precio_maximo,
        texto_nombre=texto_nombre,
    )
