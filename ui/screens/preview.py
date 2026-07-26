"""Pantalla para revisar una importación válida."""

from ui.components.messages import mostrar_mensajes
from ui.components.product_table import mostrar_productos
from ui.components.progress import mostrar_progreso
from ui.navigation import CARGA, CONFIGURACION, ir_a
from ui.session import confirmar_importacion


def renderizar(st, estado):
    mostrar_progreso(st, "vista_previa")
    st.title("Revisa tus productos")
    st.success("El archivo se validó correctamente.")
    st.write(f"**Archivo:** {estado['nombre_archivo']}")
    st.metric("Productos válidos", estado["total_productos"])
    st.caption("Vista previa de hasta 10 productos")
    mostrar_productos(st, estado["vista_previa"])
    mostrar_mensajes(st, advertencias=estado.get("advertencias"))

    confirmar, reemplazar = st.columns(2)
    if confirmar.button("Continuar a configurar", type="primary"):
        if confirmar_importacion(estado):
            ir_a(estado, CONFIGURACION)
            st.rerun()

    if reemplazar.button("Elegir otro archivo"):
        ir_a(estado, CARGA)
        st.rerun()
