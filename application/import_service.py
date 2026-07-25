"""Importación de productos con respuestas aptas para cualquier frontend."""

import os
import tempfile
from pathlib import Path

from application.errors import ErrorAplicacion, resultado_exitoso, resultado_fallido
from products import cargar_productos


def importar_desde_ruta(ruta, nombre_visible=None):
    try:
        ruta = Path(ruta)
    except TypeError:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="archivo_invalido",
                mensaje="Selecciona una ruta de archivo válida.",
                campo="archivo",
            )
        )

    nombre_visible = str(nombre_visible or ruta)

    if ruta.suffix.casefold() != ".csv":
        return resultado_fallido(
            ErrorAplicacion(
                codigo="archivo_formato_invalido",
                mensaje="Selecciona un archivo con extensión .csv.",
                campo="archivo",
            )
        )

    try:
        productos = cargar_productos(ruta)
    except FileNotFoundError:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="archivo_no_encontrado",
                mensaje=f"No se encontró el archivo: {nombre_visible}.",
                campo="archivo",
            )
        )
    except (OSError, UnicodeError, ValueError) as error:
        mensaje = str(error).replace(str(ruta), nombre_visible)
        return resultado_fallido(
            ErrorAplicacion(
                codigo="archivo_invalido",
                mensaje=mensaje,
                campo="archivo",
            )
        )
    except Exception:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="archivo_no_procesable",
                mensaje=(
                    "No se pudo procesar el archivo. "
                    "Comprueba su contenido e inténtalo nuevamente."
                ),
                campo="archivo",
            )
        )

    if not productos:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="archivo_vacio",
                mensaje="El archivo no contiene productos para analizar.",
                campo="archivo",
            )
        )

    return resultado_exitoso(
        {
            "productos": productos,
            "total_productos": len(productos),
            "vista_previa": productos[:10],
        }
    )


def importar_desde_contenido(contenido, nombre_archivo="productos.csv"):
    if not isinstance(contenido, (bytes, bytearray)):
        return resultado_fallido(
            ErrorAplicacion(
                codigo="contenido_invalido",
                mensaje="El contenido del archivo debe recibirse como bytes.",
                campo="archivo",
            )
        )

    if not contenido:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="archivo_vacio",
                mensaje="El archivo está vacío.",
                campo="archivo",
            )
        )

    try:
        extension = Path(nombre_archivo).suffix.casefold()
    except TypeError:
        extension = ""

    if extension != ".csv":
        return resultado_fallido(
            ErrorAplicacion(
                codigo="archivo_formato_invalido",
                mensaje="Selecciona un archivo con extensión .csv.",
                campo="archivo",
            )
        )

    ruta_temporal = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as archivo:
            archivo.write(contenido)
            ruta_temporal = Path(archivo.name)
        return importar_desde_ruta(
            ruta_temporal,
            nombre_visible=Path(nombre_archivo).name,
        )
    except OSError:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="archivo_no_procesable",
                mensaje=(
                    "No se pudo preparar el archivo para importarlo. "
                    "Inténtalo nuevamente."
                ),
                campo="archivo",
            )
        )
    finally:
        if ruta_temporal is not None:
            try:
                os.unlink(ruta_temporal)
            except FileNotFoundError:
                pass
