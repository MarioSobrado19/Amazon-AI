"""Indicador sencillo de avance dentro del flujo principal."""


PASOS = {
    "carga": (1, "Carga"),
    "vista_previa": (2, "Revisión"),
    "configuracion": (3, "Configuración"),
    "resultados": (4, "Resultados"),
}


def mostrar_progreso(st, pantalla):
    numero, nombre = PASOS[pantalla]
    st.caption(f"Paso {numero} de 4 · {nombre}")
    st.progress(numero / 4)
