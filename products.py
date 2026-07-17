import csv

def cargar_productos():
    productos = []

    with open("data/productos.csv", newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)

        for fila in lector:
            productos.append({
                "nombre": fila["nombre"],
                "costo": float(fila["costo"]),
                "precio": float(fila["precio"])
            })

    return productos