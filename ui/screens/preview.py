"""Pantalla para revisar una importación válida."""

from ui.components.messages import mostrar_mensajes
from ui.components.product_table import mostrar_productos
from ui.navigation import CARGA, PRODUCTOS_LISTOS, ir_a
from ui.session import confirmar_importacion


def renderizar(st, estado):
    st.title("Revisa tus productos")
    st.success("El archivo se validó correctamente.")
    st.write(f"**Archivo:** {estado['nombre_archivo']}")
    st.metric("Productos válidos", estado["total_productos"])
    st.caption("Vista previa de hasta 10 productos")
    mostrar_productos(st, estado["vista_previa"])
    mostrar_mensajes(st, advertencias=estado.get("advertencias"))

    confirmar, reemplazar = st.columns(2)
    if confirmar.button("Usar estos productos", type="primary"):
        if confirmar_importacion(estado):
            ir_a(estado, PRODUCTOS_LISTOS)
            st.rerun()

    if reemplazar.button("Elegir otro archivo"):
        ir_a(estado, CARGA)
        st.rerun()
