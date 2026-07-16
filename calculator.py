def calcular_rentabilidad(nombre, costo, precio):
    envio = 3
    tarifa_amazon = precio * 0.15
    otros_costos = 1

    costo_total = costo + envio + tarifa_amazon + otros_costos
    ganancia = precio - costo_total
    margen = (ganancia / precio) * 100
    roi = (ganancia / costo) * 100

    return {
        "nombre": nombre,
        "precio": precio,
        "costo_total": round(costo_total, 2),
        "ganancia": round(ganancia, 2),
        "margen": round(margen, 1),
        "roi": round(roi, 1)
    }