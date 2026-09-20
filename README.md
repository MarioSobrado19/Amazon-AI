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

## Interfaz de la Beta

La primera interfaz permite cargar y validar un CSV, revisar una vista previa y
confirmar que los productos están listos para analizar.

```bash
python3 -m venv .venv-ui
source .venv-ui/bin/activate
pip install -r requirements.txt
streamlit run ui/app.py
```

La aplicación abrirá una dirección local en el navegador. El análisis, los
filtros y los reportes seguirán disponibles desde `main.py` mientras se integran
progresivamente en la interfaz.

La pantalla inicial también permite analizar un producto identificado por GTIN
contra listings activos de eBay Production cuando las credenciales y la
aprobación están configuradas localmente. Ese flujo valida identidad y
presentación, compara precios observables y calcula escenarios financieros por
listing. No interpreta listings como ventas ni autoriza compras.

Para habilitar ese recorrido, el entorno debe tener configuradas localmente
`EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_ENVIRONMENT=production` y
`EBAY_BUY_PRODUCTION_APPROVED=true`. Los secretos no se introducen en la UI ni
se guardan en el repositorio. Si la conexión no está lista, la pantalla informa
qué configuración falta y mantiene deshabilitada la consulta.

Después del análisis, Oriva prepara un expediente descargable que separa datos
observados, supuestos declarados y datos todavía desconocidos. El expediente
conserva los escenarios financieros y explica el siguiente paso de investigación,
pero nunca autoriza automáticamente una compra o inversión.

## Configuración

Los valores editables están en `config.json`:

```json
{
  "rutas": {
    "datos": "data/productos.csv",
    "reportes": "reports"
  },
  "costos": {
    "envio_predeterminado": 3.0,
    "tarifa_amazon_porcentaje": 0.15,
    "otros_costos_predeterminados": 1.0
  },
  "filtros": {
    "roi_minimo": null,
    "margen_minimo": null,
    "ganancia_minima": null,
    "precio_maximo": null,
    "texto_nombre": null
  },
  "analisis": {
    "roi_excelente": 150,
    "roi_bueno": 100,
    "roi_regular": 50
  }
}
```

Las rutas deben ser relativas a la carpeta del proyecto. La tarifa se expresa como
decimal: `0.15` equivale al 15 %. El programa valida la configuración antes de
procesar productos y muestra un error claro cuando encuentra un valor inválido.

Los filtros son opcionales: usa un número mínimo para ROI, margen o ganancia; un
precio máximo; o texto contenido en el nombre. Deja un filtro en `null` para
desactivarlo. Los criterios activos se combinan y se aplican antes de mostrar y
exportar los resultados.

Los niveles de `analisis` controlan la clasificación por ROI. Deben estar
ordenados de mayor a menor: `roi_excelente >= roi_bueno >= roi_regular`.
Los valores predeterminados conservan las clasificaciones originales.

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

## Documentación

- [Índice de documentación](docs/README.md)
- [Modelo de dominio oficial de Oriva](docs/domain/ORIVA_DOMAIN_MODEL.md)
- [Decisiones de arquitectura](docs/adr/)

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
├── ui/             # Interfaz web local de la Beta
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
