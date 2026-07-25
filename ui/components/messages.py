"""Presentación uniforme de errores y advertencias."""


def mostrar_mensajes(st, errores=None, advertencias=None):
    for mensaje in errores or []:
        st.error(mensaje)
    for mensaje in advertencias or []:
        st.warning(mensaje)
