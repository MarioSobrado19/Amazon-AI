from products import cargar_productos
from report import generar_reporte
from exporter import exportar_csv
from scout import analizar_productos


products = cargar_productos()
resultados = analizar_productos(products)

print("=" * 60)
print("🚀 AMAZON SCOUT AI")
print("=" * 60)
for posicion, resultado in enumerate(resultados, start=1):
    if resultado["ganancia"] > 0:

        print()
        print(f"#{posicion} 📦 {resultado['nombre']}")
        print(f"Precio: ${resultado['precio']}")
        print(f"Costo total: ${resultado['costo_total']}")
        print(f"Ganancia: ${resultado['ganancia']}")
        print(f"Margen: {resultado['margen']}%")
        print(f"ROI: {resultado['roi']}%")

        print(f"Evaluación: {resultado['evaluacion']}")

        print()

ruta_txt = generar_reporte(resultados)
ruta_csv = exportar_csv(resultados)

print(f"✅ Reporte TXT guardado en {ruta_txt}")
print(f"✅ Reporte CSV guardado en {ruta_csv}")
