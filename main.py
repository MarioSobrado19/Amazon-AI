print("=" * 50)
print("AMAZON SCOUT AI — CALCULADORA DE PRODUCTOS")
print("=" * 50)

producto = input("\nNombre del producto: ")

precio_venta = float(input("Precio de venta en Amazon: $"))
costo_producto = float(input("Costo del producto: $"))
envio = float(input("Costo de envío por unidad: $"))
tarifas_amazon = float(input("Tarifas estimadas de Amazon: $"))
otros_costos = float(input("Otros costos por unidad: $"))

costo_total = costo_producto + envio + tarifas_amazon + otros_costos
ganancia = precio_venta - costo_total

if precio_venta > 0:
    margen = (ganancia / precio_venta) * 100
else:
    margen = 0

if costo_total > 0:
    roi = (ganancia / costo_total) * 100
else:
    roi = 0

print("\n" + "=" * 50)
print(f"RESULTADOS: {producto}")
print("=" * 50)
print(f"Precio de venta:      ${precio_venta:.2f}")
print(f"Costo total:          ${costo_total:.2f}")
print(f"Ganancia por unidad:  ${ganancia:.2f}")
print(f"Margen de ganancia:   {margen:.1f}%")
print(f"ROI estimado:         {roi:.1f}%")

if ganancia <= 0:
    print("\nEvaluación: NO RENTABLE")
elif margen < 15:
    print("\nEvaluación: MARGEN MUY BAJO")
elif margen < 25:
    print("\nEvaluación: POSIBLE, PERO HAY QUE INVESTIGAR MÁS")
else:
    print("\nEvaluación: PRODUCTO INTERESANTE PARA ANALIZAR")