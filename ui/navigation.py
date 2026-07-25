"""Reglas de navegación independientes de Streamlit."""


BIENVENIDA = "bienvenida"
CARGA = "carga"
VISTA_PREVIA = "vista_previa"
PRODUCTOS_LISTOS = "productos_listos"

PANTALLAS = {
    BIENVENIDA,
    CARGA,
    VISTA_PREVIA,
    PRODUCTOS_LISTOS,
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
    return True


def ir_a(estado, pantalla):
    if not puede_ir_a(estado, pantalla):
        estado["pantalla_actual"] = BIENVENIDA
        return False

    estado["pantalla_actual"] = pantalla
    return True
