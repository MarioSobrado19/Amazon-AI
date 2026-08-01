"""Presentación de la oportunidad principal del análisis."""

from ui.components.opportunity import mostrar_detalle_oportunidad


def mostrar_mejor_producto(st, producto):
    st.subheader("🏆 Mejor oportunidad por ROI")
    with st.container(border=True):
        st.markdown(f"### {producto['nombre']}")
        columnas = st.columns(4)
        columnas[0].metric("ROI estimado", f"{producto['roi']:.1f}%")
        columnas[1].metric("Ganancia estimada", f"${producto['ganancia']:.2f}")
        columnas[2].metric("Margen", f"{producto['margen']:.1f}%")
        puntaje = producto.get("opportunity_score")
        columnas[3].metric(
            "Score financiero estimado",
            f"{puntaje:.1f}/100" if puntaje is not None else "—",
        )
        categoria = producto.get("opportunity_category")
        mensaje = producto["evaluacion"].title()
        if categoria:
            mensaje = f"{mensaje} · {categoria}"
        st.success(mensaje)
        mostrar_detalle_oportunidad(st, producto)
