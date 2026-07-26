"""Confirmación final del flujo de Sprint 11."""

from ui.navigation import CONFIGURACION, VISTA_PREVIA, ir_a
from ui.session import reiniciar_sesion


def renderizar(st, estado):
    st.title("✅ Productos listos")
    st.success(
        f"Importaste correctamente {estado['total_productos']} productos desde "
        f"{estado['nombre_archivo']}."
    )
    st.write("Tus datos están preparados para configurar y ejecutar el análisis.")
    if st.button("Configurar análisis", type="primary"):
        ir_a(estado, CONFIGURACION)
        st.rerun()

    revisar, nuevo = st.columns(2)
    if revisar.button("← Revisar productos"):
        estado["importacion_confirmada"] = False
        ir_a(estado, VISTA_PREVIA)
        st.rerun()
    if nuevo.button("Comenzar un análisis nuevo"):
        reiniciar_sesion(estado)
        st.rerun()
