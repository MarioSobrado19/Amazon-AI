"""Presentación del Decision Engine sin reglas de decisión en la interfaz."""


def _mostrar_lista(st, titulo, elementos):
    if elementos:
        st.markdown(f"**{titulo}**")
        for elemento in elementos:
            st.markdown(f"- {elemento}")


def mostrar_decision(st, decision):
    st.subheader("Apoyo para tu próxima decisión")
    with st.container(border=True):
        st.caption(
            f"Situación actual: {decision['estado'].title()} · "
            f"Confianza {decision['nivel_confianza']}"
        )
        st.markdown(f"### {decision['recomendacion_principal']}")
        st.write(decision["resumen"])

        _mostrar_lista(st, "Por qué", decision["evidencia_favorable"])
        if decision["riesgos"]:
            st.warning(f"Riesgo principal: {decision['riesgos'][0]}")
        _mostrar_lista(st, "Datos que faltan", decision["datos_faltantes"])

        st.markdown("**Próximo paso**")
        st.info(decision["proximo_paso"])
        _mostrar_lista(st, "Alternativas", decision["alternativas"])
        st.markdown(f"**Pregunta para continuar:** {decision['pregunta_de_continuacion']}")

        with st.expander("Condiciones, reglas y limitaciones"):
            _mostrar_lista(
                st,
                "Condiciones para avanzar",
                decision["condiciones_para_avanzar"],
            )
            _mostrar_lista(st, "Reglas aplicadas", decision["reglas_aplicadas"])
            _mostrar_lista(st, "Limitaciones", decision["limitaciones"])
