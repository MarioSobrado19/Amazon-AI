import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = BASE_DIR / "config.json"


def _obtener_seccion(configuracion, nombre):
    seccion = configuracion.get(nombre)
    if not isinstance(seccion, dict):
        raise ValueError(f"La configuración debe incluir la sección '{nombre}'.")
    return seccion


def _obtener_numero(seccion, nombre, propiedad, minimo=0, maximo=None):
    if nombre not in seccion:
        raise ValueError(f"Falta la propiedad '{propiedad}'.")

    valor = seccion[nombre]
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"'{propiedad}' debe ser un número.")
    if valor < minimo or (maximo is not None and valor > maximo):
        limite = (
            f" entre {minimo} y {maximo}"
            if maximo is not None
            else f" mayor o igual a {minimo}"
        )
        raise ValueError(f"'{propiedad}' debe ser{limite}.")
    return float(valor)


def _resolver_ruta(base_dir, valor, nombre):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"'{nombre}' debe ser una ruta relativa no vacía.")

    ruta_relativa = Path(valor)
    if ruta_relativa.is_absolute():
        raise ValueError(f"'{nombre}' debe ser una ruta relativa al proyecto.")
    if ".." in ruta_relativa.parts:
        raise ValueError(f"'{nombre}' no puede contener '..'.")

    ruta_resuelta = (base_dir / ruta_relativa).resolve()
    try:
        ruta_resuelta.relative_to(base_dir.resolve())
    except ValueError as error:
        raise ValueError(f"'{nombre}' no puede salir de la carpeta del proyecto.") from error

    return ruta_resuelta


def cargar_configuracion(ruta=_CONFIG_FILE, base_dir=BASE_DIR):
    ruta = Path(ruta)
    base_dir = Path(base_dir).resolve()

    try:
        with open(ruta, encoding="utf-8") as archivo:
            configuracion = json.load(archivo)
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"No se encontró el archivo de configuración: {ruta}"
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"El archivo de configuración no contiene JSON válido: {ruta}"
        ) from error

    if not isinstance(configuracion, dict):
        raise ValueError("La configuración principal debe ser un objeto JSON.")

    rutas = _obtener_seccion(configuracion, "rutas")
    costos = _obtener_seccion(configuracion, "costos")

    return {
        "data_file": _resolver_ruta(
            base_dir,
            rutas.get("datos"),
            "rutas.datos",
        ),
        "reports_dir": _resolver_ruta(
            base_dir,
            rutas.get("reportes"),
            "rutas.reportes",
        ),
        "envio_predeterminado": _obtener_numero(
            costos,
            "envio_predeterminado",
            "costos.envio_predeterminado",
        ),
        "tarifa_amazon_porcentaje": _obtener_numero(
            costos,
            "tarifa_amazon_porcentaje",
            "costos.tarifa_amazon_porcentaje",
            maximo=1,
        ),
        "otros_costos_predeterminados": _obtener_numero(
            costos,
            "otros_costos_predeterminados",
            "costos.otros_costos_predeterminados",
        ),
    }


_CONFIGURACION = cargar_configuracion()

DATA_FILE = _CONFIGURACION["data_file"]
REPORTS_DIR = _CONFIGURACION["reports_dir"]
ENVIO_PREDETERMINADO = _CONFIGURACION["envio_predeterminado"]
TARIFA_AMAZON_PORCENTAJE = _CONFIGURACION["tarifa_amazon_porcentaje"]
OTROS_COSTOS_PREDETERMINADOS = _CONFIGURACION["otros_costos_predeterminados"]
