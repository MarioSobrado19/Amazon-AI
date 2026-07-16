from products import products
from calculator import calcular_rentabilidad

print("=" * 60)
print("🚀 AMAZON SCOUT AI")
print("=" * 60)

for producto in products:

    resultado = calcular_rentabilidad(
        producto["nombre"],
        producto["costo"],
        producto["precio"]
    )

    print()
    print(f"📦 {resultado['nombre']}")
    print(f"Precio: ${resultado['precio']}")
    print(f"Costo total: ${resultado['costo_total']}")
    print(f"Ganancia: ${resultado['ganancia']}")
    print(f"Margen: {resultado['margen']}%")
    print(f"ROI: {resultado['roi']}%")