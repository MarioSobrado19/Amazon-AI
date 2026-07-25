"""Pantalla para cargar y validar un CSV."""

from application import importar_desde_contenido
from ui.components.messages import mostrar_mensajes
from ui.navigation import BIENVENIDA, VISTA_PREVIA, ir_a
from ui.session import guardar_importacion
from ui.view_models import PLANTILLA_CSV, mensajes_de_error


def renderizar(st, estado):
    st.title("Carga tus productos")
    st.write("El archivo debe contener las columnas `nombre`, `costo` y `precio`.")
    st.code("nombre,costo,precio\nOrganizador de cocina,8,29.99", language="csv")

    archivo = st.file_uploader("Selecciona un archivo CSV", type=["csv"])
    st.download_button(
        "Descargar plantilla",
        data=PLANTILLA_CSV,
        file_name="plantilla_productos.csv",
        mime="text/csv",
    )

    if archivo is not None and st.button("Validar archivo", type="primary"):
        resultado = importar_desde_contenido(archivo.getvalue(), archivo.name)
        if resultado["exito"]:
            guardar_importacion(
                estado,
                archivo.name,
                resultado["datos"],
                resultado["advertencias"],
            )
            ir_a(estado, VISTA_PREVIA)
            st.rerun()
        else:
            estado["errores"] = mensajes_de_error(resultado)

    mostrar_mensajes(st, estado.get("errores"), estado.get("advertencias"))

    if st.button("← Volver al inicio"):
        ir_a(estado, BIENVENIDA)
        st.rerun()
