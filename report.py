def generar_reporte(productos):
    with open("reports/mejores_productos.txt", "w", encoding="utf-8") as archivo:

        archivo.write("🚀 AMAZON SCOUT AI\n")
        archivo.write("=" * 40 + "\n\n")

        for posicion, producto in enumerate(productos, start=1):

            archivo.write(f"#{posicion} {producto['nombre']}\n")
            archivo.write(f"ROI: {producto['roi']}%\n")
            archivo.write(f"Ganancia: ${producto['ganancia']}\n")
            archivo.write("\n")