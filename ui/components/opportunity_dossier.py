"""Vista del expediente auditable de una oportunidad."""

from application.opportunity_dossier_service import (
    exportar_expediente_json,
    exportar_expediente_txt,
)


EVIDENCE_LABELS = {
    "active_listings": "Listings activos observados",
    "exact_gtin_matches": "Coincidencias confirmadas por GTIN",
    "observable_advertised_price_range": "Rango de precios anunciados",
    "purchase_cost": "Costo de compra declarado",
    "financial_cost_assumptions": "Tarifas y costos asumidos",
}


def mostrar_expediente(st, dossier):
    st.divider()
    st.header("Expediente de oportunidad")
    guidance = dossier["guidance"]
    market = dossier["market"]
    st.info(guidance["headline"])
    st.write(guidance["why"])

    columnas = st.columns(4)
    columnas[0].metric("Estado", guidance["state"].capitalize())
    columnas[1].metric("Listings", market["active_listings_observed"])
    columnas[2].metric("Comparables", market["usable_comparables"])
    columnas[3].metric("Precio representativo", (
        f"${market['representative_price']:.2f}"
        if market["representative_price"] is not None else "No disponible"
    ))

    st.subheader("Qué sabemos")
    for item in dossier["evidence"]["observed"]:
        label = EVIDENCE_LABELS.get(item["field"], item["field"])
        st.write(f"• **{label}:** {item['meaning']}")

    st.subheader("Qué estamos suponiendo")
    for item in dossier["evidence"]["assumptions"]:
        label = EVIDENCE_LABELS.get(item["field"], item["field"])
        st.write(f"• **{label}:** {item['meaning']}")

    st.subheader("Qué falta verificar")
    for item in dossier["evidence"]["unknown"]:
        st.write(f"• {item}")

    st.subheader("Siguiente paso razonable")
    st.write(guidance["next_step"])
    st.warning(
        "La decisión final permanece en tus manos. Este expediente no autoriza "
        "comprar inventario ni invertir."
    )

    json_export = exportar_expediente_json(dossier)
    text_export = exportar_expediente_txt(dossier)
    downloads = st.columns(2)
    downloads[0].download_button(
        "Descargar expediente JSON",
        data=json_export["contenido"],
        file_name=json_export["nombre_archivo"],
        mime=json_export["mime"],
    )
    downloads[1].download_button(
        "Descargar resumen TXT",
        data=text_export["contenido"],
        file_name=text_export["nombre_archivo"],
        mime=text_export["mime"],
    )
