"""Estado del recorrido visual, sin dependencias de interfaz."""

from ui.navigation import BIENVENIDA


ESTADO_INICIAL = {
    "pantalla_actual": BIENVENIDA,
    "nombre_archivo": None,
    "productos": [],
    "total_productos": 0,
    "vista_previa": [],
    "errores": [],
    "advertencias": [],
    "importacion_confirmada": False,
}


def inicializar_sesion(estado):
    for clave, valor in ESTADO_INICIAL.items():
        if clave not in estado:
            estado[clave] = valor.copy() if isinstance(valor, list) else valor


def guardar_importacion(estado, nombre_archivo, datos, advertencias=None):
    estado["nombre_archivo"] = nombre_archivo
    estado["productos"] = list(datos["productos"])
    estado["total_productos"] = datos["total_productos"]
    estado["vista_previa"] = list(datos["vista_previa"])
    estado["errores"] = []
    estado["advertencias"] = list(advertencias or [])
    estado["importacion_confirmada"] = False


def confirmar_importacion(estado):
    if not estado.get("productos"):
        return False
    estado["importacion_confirmada"] = True
    return True


def reiniciar_sesion(estado):
    for clave, valor in ESTADO_INICIAL.items():
        estado[clave] = valor.copy() if isinstance(valor, list) else valor
