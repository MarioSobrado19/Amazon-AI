"""Confirmación final del flujo de Sprint 11."""

from ui.navigation import VISTA_PREVIA, ir_a
from ui.session import reiniciar_sesion


def renderizar(st, estado):
    st.title("✅ Productos listos")
    st.success(
        f"Importaste correctamente {estado['total_productos']} productos desde "
        f"{estado['nombre_archivo']}."
    )
    st.write(
        "Tus datos están preparados. En el siguiente sprint podrás configurar "
        "los criterios y ejecutar el análisis desde esta misma aplicación."
    )
    st.button("Continuar al análisis (próximamente)", disabled=True)

    revisar, nuevo = st.columns(2)
    if revisar.button("← Revisar productos"):
        estado["importacion_confirmada"] = False
        ir_a(estado, VISTA_PREVIA)
        st.rerun()
    if nuevo.button("Comenzar un análisis nuevo"):
        reiniciar_sesion(estado)
        st.rerun()
