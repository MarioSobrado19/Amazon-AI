import csv

from config import REPORTS_DIR


def exportar_csv(productos):
    REPORTS_DIR.mkdir(exist_ok=True)
    ruta = REPORTS_DIR / "mejores_productos.csv"

    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        campos = [
            "posicion",
            "nombre",
            "precio",
            "costo_total",
            "ganancia",
            "margen",
            "roi",
            "evaluacion",
        ]

        escritor = csv.DictWriter(archivo, fieldnames=campos, lineterminator="\n")
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
                    "evaluacion": producto["evaluacion"],
                }
            )

    return ruta
