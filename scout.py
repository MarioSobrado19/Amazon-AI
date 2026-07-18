from calculator import calcular_rentabilidad


def clasificar_producto(roi):
    if roi >= 150:
        return "EXCELENTE PRODUCTO"
    if roi >= 100:
        return "BUEN PRODUCTO"
    if roi >= 50:
        return "REGULAR"
    return "NO RECOMENDADO"


def analizar_productos(productos):
    resultados = []

    for producto in productos:
        resultado = calcular_rentabilidad(
            producto["nombre"],
            producto["costo"],
            producto["precio"],
        )
        resultado["evaluacion"] = clasificar_producto(resultado["roi"])
        resultados.append(resultado)

    return sorted(resultados, key=lambda producto: producto["roi"], reverse=True)
