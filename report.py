from config import REPORTS_DIR


def generar_reporte(productos):
    REPORTS_DIR.mkdir(exist_ok=True)
    ruta = REPORTS_DIR / "mejores_productos.txt"

    with open(ruta, "w", encoding="utf-8") as archivo:

        archivo.write("🚀 AMAZON SCOUT AI\n")
        archivo.write("=" * 40 + "\n\n")

        for posicion, producto in enumerate(productos, start=1):

            archivo.write(f"#{posicion} {producto['nombre']}\n")
            archivo.write(f"ROI: {producto['roi']}%\n")
            archivo.write(f"Ganancia: ${producto['ganancia']}\n")
            archivo.write(f"Evaluación: {producto['evaluacion']}\n")
            archivo.write("\n")

    return ruta
