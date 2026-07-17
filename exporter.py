import csv


def exportar_csv(productos):
    ruta = "reports/mejores_productos.csv"

    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        campos = [
            "posicion",
            "nombre",
            "precio",
            "costo_total",
            "ganancia",
            "margen",
            "roi",
        ]

        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()

        for posicion, producto in enumerate(productos, start=1):
            escritor.writerow(
                {
                    "posicion": posicion,
                    "nombre": producto["nombre"],
                    "precio": producto["precio"],
                    "costo_total": producto["costo_total"],
                    "ganancia": producto["ganancia"],
                    "margen": producto["margen"],
                    "roi": producto["roi"],
                }
            )

    return ruta