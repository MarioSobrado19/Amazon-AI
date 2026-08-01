"""Presentación visual de insights deterministas."""


def _mostrar_lista(st, titulo, elementos):
    if elementos:
        st.markdown(f"**{titulo}**")
        for elemento in elementos:
            st.markdown(f"- {elemento}")


def mostrar_insights(st, insights):
    st.subheader("Lectura inteligente de resultados")
    with st.container(border=True):
        st.markdown(f"### {insights['titular_principal']}")
        st.write(insights["resumen_ejecutivo"])

        producto = insights.get("producto_prioritario")
        if producto:
            st.info(f"Producto prioritario: **{producto['nombre']}**")

        _mostrar_lista(st, "Fortalezas", insights["fortalezas_detectadas"])
        _mostrar_lista(st, "Riesgos", insights["riesgos_detectados"])
        _mostrar_lista(
            st,
            "Próximos pasos",
            insights["proximos_pasos_recomendados"],
        )

        with st.expander("Limitaciones del análisis"):
            for advertencia in insights["advertencias"]:
                st.caption(advertencia)
