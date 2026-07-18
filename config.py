from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "productos.csv"
REPORTS_DIR = BASE_DIR / "reports"

ENVIO_PREDETERMINADO = 3.0
TARIFA_AMAZON_PORCENTAJE = 0.15
OTROS_COSTOS_PREDETERMINADOS = 1.0
