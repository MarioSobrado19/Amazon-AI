import csv

from config import DATA_FILE


CAMPOS_REQUERIDOS = {"nombre", "costo", "precio"}


def cargar_productos(ruta=DATA_FILE):
    productos = []

    with open(ruta, newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)

        if not lector.fieldnames or not CAMPOS_REQUERIDOS.issubset(lector.fieldnames):
            raise ValueError(
                "El CSV debe incluir las columnas: nombre, costo y precio."
            )

        for numero_fila, fila in enumerate(lector, start=2):
            try:
                nombre = fila["nombre"].strip()
                costo = float(fila["costo"])
                precio = float(fila["precio"])
            except (AttributeError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Datos inválidos en la fila {numero_fila} de {ruta}."
                ) from error

            if not nombre:
                raise ValueError(f"Falta el nombre en la fila {numero_fila}.")
            if costo <= 0 or precio <= 0:
                raise ValueError(
                    f"Costo y precio deben ser mayores que cero en la fila {numero_fila}."
                )

            productos.append(
                {"nombre": nombre, "costo": costo, "precio": precio}
            )

    return productos
