"""Contratos uniformes para resultados y errores de la capa de aplicación."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ErrorAplicacion:
    codigo: str
    mensaje: str
    campo: str | None = None
    fila: int | None = None

    def como_dict(self):
        return asdict(self)


def resultado_exitoso(datos=None, advertencias=None):
    return {
        "exito": True,
        "datos": datos,
        "errores": [],
        "advertencias": list(advertencias or []),
    }


def resultado_fallido(errores, datos=None, advertencias=None):
    if isinstance(errores, ErrorAplicacion):
        errores = [errores]

    return {
        "exito": False,
        "datos": datos,
        "errores": [
            error.como_dict() if isinstance(error, ErrorAplicacion) else error
            for error in errores
        ],
        "advertencias": list(advertencias or []),
    }
