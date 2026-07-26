"""Reglas de navegación independientes de Streamlit."""


BIENVENIDA = "bienvenida"
CARGA = "carga"
VISTA_PREVIA = "vista_previa"
PRODUCTOS_LISTOS = "productos_listos"
CONFIGURACION = "configuracion"
RESULTADOS = "resultados"

PANTALLAS = {
    BIENVENIDA,
    CARGA,
    VISTA_PREVIA,
    PRODUCTOS_LISTOS,
    CONFIGURACION,
    RESULTADOS,
}


def puede_ir_a(estado, pantalla):
    if pantalla not in PANTALLAS:
        return False
    if pantalla == VISTA_PREVIA:
        return bool(estado.get("productos"))
    if pantalla == PRODUCTOS_LISTOS:
        return bool(estado.get("productos")) and bool(
            estado.get("importacion_confirmada")
        )
    if pantalla == CONFIGURACION:
        return bool(estado.get("productos")) and bool(
            estado.get("importacion_confirmada")
        )
    if pantalla == RESULTADOS:
        return estado.get("resultados") is not None
    return True


def ir_a(estado, pantalla):
    if not puede_ir_a(estado, pantalla):
        estado["pantalla_actual"] = BIENVENIDA
        return False

    estado["pantalla_actual"] = pantalla
    return True
