"""Pantalla de bienvenida."""

from ui.navigation import CARGA, ir_a
from ui.view_models import PLANTILLA_CSV


def renderizar(st, estado):
    st.title("🚀 Amazon Scout AI")
    st.subheader("Prioriza productos por rentabilidad en pocos minutos")
    st.write(
        "Carga un CSV con nombre, costo y precio. Obtendrás un ranking con ROI, "
        "margen y ganancia estimada para decidir qué investigar primero."
    )

    columnas = st.columns(3)
    columnas[0].markdown("### 1. Carga\nSube tu archivo CSV.")
    columnas[1].markdown("### 2. Revisa\nConfirma que los datos sean correctos.")
    columnas[2].markdown("### 3. Decide\nCompara y descarga los resultados.")

    st.info(
        "Los resultados son estimaciones educativas y no garantizan rentabilidad."
    )
    st.download_button(
        "Descargar plantilla CSV",
        data=PLANTILLA_CSV,
        file_name="plantilla_productos.csv",
        mime="text/csv",
    )
    if st.button("Analizar mis productos", type="primary"):
        ir_a(estado, CARGA)
        st.rerun()
