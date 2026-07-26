"""Presentación de la oportunidad principal del análisis."""


def mostrar_mejor_producto(st, producto):
    st.subheader("🏆 Mejor oportunidad por ROI")
    with st.container(border=True):
        st.markdown(f"### {producto['nombre']}")
        columnas = st.columns(3)
        columnas[0].metric("ROI estimado", f"{producto['roi']:.1f}%")
        columnas[1].metric("Ganancia estimada", f"${producto['ganancia']:.2f}")
        columnas[2].metric("Margen", f"{producto['margen']:.1f}%")
        st.success(producto["evaluacion"].title())
