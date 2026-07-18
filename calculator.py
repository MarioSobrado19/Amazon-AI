from config import (
    ENVIO_PREDETERMINADO,
    OTROS_COSTOS_PREDETERMINADOS,
    TARIFA_AMAZON_PORCENTAJE,
)


def calcular_rentabilidad(
    nombre,
    costo,
    precio,
    envio=ENVIO_PREDETERMINADO,
    otros_costos=OTROS_COSTOS_PREDETERMINADOS,
):
    if costo <= 0:
        raise ValueError("El costo debe ser mayor que cero.")
    if precio <= 0:
        raise ValueError("El precio debe ser mayor que cero.")

    tarifa_amazon = precio * TARIFA_AMAZON_PORCENTAJE

    costo_total = costo + envio + tarifa_amazon + otros_costos
    ganancia = precio - costo_total
    margen = (ganancia / precio) * 100
    roi = (ganancia / costo) * 100

    return {
        "nombre": nombre,
        "precio": precio,
        "costo_producto": costo,
        "envio": envio,
        "tarifa_amazon": round(tarifa_amazon, 2),
        "otros_costos": otros_costos,
        "costo_total": round(costo_total, 2),
        "ganancia": round(ganancia, 2),
        "margen": round(margen, 1),
        "roi": round(roi, 1)
    }
