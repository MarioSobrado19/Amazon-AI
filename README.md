# Amazon Scout AI

Herramienta educativa en Python para comparar productos por rentabilidad. Lee un
archivo CSV, calcula ganancia, margen y retorno sobre inversión (ROI), ordena los
resultados y genera reportes en TXT y CSV.

> Estado: prototipo local. Los datos incluidos son ejemplos; todavía no consulta
> precios, ventas ni tarifas oficiales de Amazon.

## Funciones actuales

- Carga y valida productos desde `data/productos.csv`.
- Estima una tarifa de Amazon del 15 %, envío y otros costos.
- Calcula costo total, ganancia, margen y ROI.
- Clasifica y ordena productos de mayor a menor ROI.
- Genera reportes en `reports/mejores_productos.txt` y `.csv`.
- Incluye pruebas automáticas para proteger los cálculos principales.

## Ejecutar el proyecto

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 main.py
```

No requiere paquetes externos: usa solamente la biblioteca estándar de Python.

## Formato de entrada

Edita `data/productos.csv` manteniendo estas columnas:

```csv
nombre,costo,precio
Organizador de cocina,8,29.99
```

- `costo`: costo de compra por unidad.
- `precio`: precio estimado de venta por unidad.

## Pruebas

```bash
python3 -m unittest discover -s tests
```

## Estructura

```text
Amazon-AI/
├── calculator.py   # Fórmulas de rentabilidad
├── config.py       # Rutas y supuestos configurables
├── data/           # Datos de entrada
├── exporter.py     # Exportación CSV
├── main.py         # Punto de entrada
├── products.py     # Carga y validación del CSV
├── report.py       # Reporte de texto
├── reports/        # Reportes generados
├── scout.py        # Análisis, clasificación y ranking
└── tests/          # Pruebas automáticas
```

## Próximo paso: datos reales

La siguiente etapa debe usar una fuente autorizada y estable, como Amazon Selling
Partner API para una cuenta elegible o un proveedor de datos con licencia. Antes de
conectarla se añadirá una capa independiente de importación, para que los cálculos
actuales no dependan de una sola fuente ni se rompan al cambiar de proveedor.

No se recomienda extraer páginas de Amazon directamente: es frágil, puede producir
datos incorrectos y puede incumplir condiciones del servicio.

## Aviso

Las cifras son estimaciones educativas, no asesoría financiera ni una garantía de
rentabilidad. Antes de comprar inventario deben verificarse tarifas FBA, impuestos,
devoluciones, almacenamiento, publicidad y demanda real.
