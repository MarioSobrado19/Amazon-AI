"""Pantalla de bienvenida."""

from ui.navigation import CARGA, ir_a
from ui.view_models import PLANTILLA_CSV


def renderizar(st, estado):
    st.title("🚀 Amazon Scout AI")
    st.subheader("Encuentra qué productos merecen una investigación más profunda")
    st.write(
        "Carga una lista de productos y conviértela en información clara para "
        "comparar oportunidades de venta."
    )

    columnas = st.columns(3)
    columnas[0].markdown("### 1. Carga\nSube tu archivo CSV.")
    columnas[1].markdown("### 2. Revisa\nConfirma que los datos sean correctos.")
    columnas[2].markdown("### 3. Analiza\nPrioriza productos por rentabilidad.")

    st.info(
        "Los resultados son estimaciones educativas y no garantizan rentabilidad."
    )
    st.download_button(
        "Descargar plantilla CSV",
        data=PLANTILLA_CSV,
        file_name="plantilla_productos.csv",
        mime="text/csv",
    )
    if st.button("Comenzar", type="primary"):
        ir_a(estado, CARGA)
        st.rerun()
