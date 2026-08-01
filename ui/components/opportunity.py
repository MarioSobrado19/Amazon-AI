"""Detalle visual y auditable del Opportunity Score."""


ETIQUETAS = {
    "roi": ("ROI", "%"),
    "margen": ("Margen", "%"),
    "ganancia": ("Ganancia", "$"),
}

DESCRIPCION_SCORE = (
    "El Opportunity Score es una evaluación financiera estimada basada "
    "únicamente en ROI, margen y ganancia."
)
LIMITACIONES_SCORE = (
    "Todavía no considera demanda, competencia, historial de precios, "
    "proveedores, velocidad de venta ni riesgo de inventario."
)


def mostrar_detalle_oportunidad(st, producto):
    factores = producto.get("opportunity_factors")
    if not factores:
        return

    st.caption(DESCRIPCION_SCORE)
    st.warning(LIMITACIONES_SCORE)
    with st.expander("¿Cómo se calculó el Opportunity Score?"):
        st.caption(
            "El puntaje combina ROI, margen y ganancia ya calculados. "
            "Cada factor tiene un límite para evitar que una sola métrica domine."
        )
        for clave in ("roi", "margen", "ganancia"):
            factor = factores[clave]
            etiqueta, simbolo = ETIQUETAS[clave]
            valor = factor["valor"]
            valor_formateado = (
                f"${valor:.2f}" if simbolo == "$" else f"{valor:.1f}%"
            )
            referencia = factor["referencia"]
            referencia_formateada = (
                f"${referencia:.2f}"
                if simbolo == "$"
                else f"{referencia:.1f}%"
            )
            st.write(
                f"**{etiqueta}:** {factor['puntos']:.1f}/{factor['maximo']:.0f} "
                f"puntos · valor observado {valor_formateado} · "
                f"máximo aporte desde {referencia_formateada}"
            )
