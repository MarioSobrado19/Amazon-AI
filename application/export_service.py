"""Coordinación uniforme de las exportaciones existentes."""

from application.errors import ErrorAplicacion, resultado_exitoso, resultado_fallido
from exporter import exportar_csv
from report import generar_reporte


EXPORTADORES = {
    "csv": exportar_csv,
    "txt": generar_reporte,
}


def exportar(resultados, formato):
    formato = str(formato).casefold().strip()
    if formato not in EXPORTADORES:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="formato_exportacion_invalido",
                mensaje="El formato debe ser 'csv' o 'txt'.",
                campo="formato",
            )
        )

    if not isinstance(resultados, list) or not resultados:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="exportacion_vacia",
                mensaje="No hay resultados para exportar.",
                campo="resultados",
            )
        )

    try:
        ruta = EXPORTADORES[formato](resultados)
        contenido = ruta.read_bytes()
    except Exception:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="exportacion_fallida",
                mensaje=(
                    f"No se pudo generar el archivo {formato.upper()}. "
                    "Inténtalo nuevamente."
                ),
            )
        )

    return resultado_exitoso(
        {
            "formato": formato,
            "nombre_archivo": ruta.name,
            "ruta": str(ruta),
            "contenido": contenido,
            "total_productos": len(resultados),
        }
    )
