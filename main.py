from products import cargar_productos
from calculator import calcular_rentabilidad
from report import generar_reporte
products = cargar_productos()
products.sort(
    key=lambda x: calcular_rentabilidad(
        x["nombre"],
        x["costo"],
        x["precio"],
    )["roi"],
    reverse=True
)

print("=" * 60)
print("🚀 AMAZON SCOUT AI")
print("=" * 60)
resultados = []
for producto in products:

    resultado = calcular_rentabilidad(
        producto["nombre"],
        producto["costo"],
        producto["precio"]
    )

    resultados.append(resultado)

    if resultado["ganancia"] > 0:

        print()
        print(f"📦 {resultado['nombre']}")
        print(f"Precio: ${resultado['precio']}")
        print(f"Costo total: ${resultado['costo_total']}")
        print(f"Ganancia: ${resultado['ganancia']}")
        print(f"Margen: {resultado['margen']}%")
        print(f"ROI: {resultado['roi']}%")

        if resultado["roi"] >= 150:
            print("⭐⭐⭐⭐⭐ EXCELENTE PRODUCTO")

        elif resultado["roi"] >= 100:
            print("⭐⭐⭐⭐ BUEN PRODUCTO")

        elif resultado["roi"] >= 50:
            print("⭐⭐⭐ REGULAR")

        else:
            print("❌ NO RECOMENDADO")

        print()

generar_reporte(resultados)

print("✅ Reporte guardado en reports/mejores_productos.txt")