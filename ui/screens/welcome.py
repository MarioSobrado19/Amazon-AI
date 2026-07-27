"""Pantalla de bienvenida."""

from ui.navigation import CARGA, ir_a
from ui.view_models import PLANTILLA_CSV


def renderizar(st, estado):
    st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)
    st.title("Encuentra productos con mayor potencial antes de invertir")
    st.caption("AMAZON SCOUT AI")
    st.markdown("<div style='height: 0.75rem'></div>", unsafe_allow_html=True)
    st.subheader("Analiza cientos de productos en segundos")
    st.write(
        "Carga un CSV con nombre, costo y precio. Obtendrás un ranking con ROI, "
        "margen y ganancia estimada para decidir qué investigar primero."
    )

    beneficios = st.columns(4)
    beneficios[0].markdown("✓ **ROI**")
    beneficios[1].markdown("✓ **Margen**")
    beneficios[2].markdown("✓ **Ganancia**")
    beneficios[3].markdown("✓ **Ranking automático**")

    st.markdown("<div style='height: 1.25rem'></div>", unsafe_allow_html=True)
    columnas = st.columns(3)
    columnas[0].markdown("### 1. Carga\nSube tu archivo CSV.")
    columnas[1].markdown("### 2. Revisa\nConfirma que los datos sean correctos.")
    columnas[2].markdown("### 3. Decide\nCompara y descarga los resultados.")

    st.info(
        "Los resultados son estimaciones basadas en la información proporcionada "
        "y sirven como apoyo para la toma de decisiones."
    )
    st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)
    st.download_button(
        "Descargar plantilla CSV",
        data=PLANTILLA_CSV,
        file_name="plantilla_productos.csv",
        mime="text/csv",
    )
    if st.button("Cargar archivo CSV", type="primary"):
        ir_a(estado, CARGA)
        st.rerun()
