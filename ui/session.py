"""Estado del recorrido visual, sin dependencias de interfaz."""

from application import CONFIGURACION_PREDETERMINADA
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
    "configuracion": CONFIGURACION_PREDETERMINADA,
    "filtros": {},
    "resultados": None,
    "resumen": None,
    "insights": None,
    "decision": None,
    "total_analizado": 0,
}


def inicializar_sesion(estado):
    for clave, valor in ESTADO_INICIAL.items():
        if clave not in estado:
            estado[clave] = valor.copy() if isinstance(valor, (list, dict)) else valor


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


def guardar_analisis(estado, datos, resumen, insights=None, decision=None):
    estado["resultados"] = list(datos["resultados"])
    estado["total_analizado"] = datos["total_analizado"]
    estado["filtros"] = dict(datos["filtros_aplicados"])
    estado["configuracion"] = dict(datos["configuracion_aplicada"])
    estado["resumen"] = dict(resumen)
    estado["insights"] = dict(insights) if insights else None
    estado["decision"] = dict(decision) if decision else None
    estado["errores"] = []


def limpiar_analisis(estado):
    estado["resultados"] = None
    estado["resumen"] = None
    estado["insights"] = None
    estado["decision"] = None
    estado["total_analizado"] = 0


def reiniciar_sesion(estado):
    for clave, valor in ESTADO_INICIAL.items():
        estado[clave] = valor.copy() if isinstance(valor, (list, dict)) else valor
