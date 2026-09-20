"""Componentes visuales del Research Workspace."""


STATUS_LABELS = {
    "missing": "Faltante",
    "partial": "Parcial",
    "documented": "Documentado",
    "stale": "Vencido",
}
CATEGORY_LABELS = {
    "demand": "Demanda",
    "supplier": "Proveedor",
    "costs": "Costos finales",
    "restrictions": "Restricciones",
    "competition": "Competencia observable",
    "marketplace": "Marketplace",
    "logistics": "Logística",
}
TYPE_LABELS = {"data": "Dato", "estimate": "Estimación", "assumption": "Supuesto"}


def coverage_rows(workspace):
    return [
        {
            "Área": item["label"],
            "Estado": STATUS_LABELS[item["status"]],
            "¿Bloquea revisión?": "Sí" if item["blocking"] else "No",
            "Explicación": item["explanation"],
            "Evidencias": len(item["evidence_ids"]),
        }
        for item in workspace["coverage"]
    ]


def evidence_rows(workspace):
    return [
        {
            "ID": item["evidence_id"][:10],
            "Área": CATEGORY_LABELS.get(item["category"], item["category"]),
            "Resumen": item["summary"],
            "Tipo": TYPE_LABELS.get(item["evidence_type"], item["evidence_type"]),
            "Fuente": item.get("source_name") or "—",
            "Referencia": item.get("source_reference") or "—",
            "Vigencia": item["freshness"],
            "Confianza": item["confidence"],
            "Origen": item["origin"],
        }
        for item in workspace["evidence"]
    ]


def mostrar_resumen_workspace(st, workspace):
    status_labels = {
        "collecting_evidence": "Recopilando evidencia",
        "needs_refresh": "Necesita actualización",
        "documented_for_review": "Documentado para revisión",
    }
    st.subheader("Estado de la investigación")
    columns = st.columns(3)
    columns[0].metric("Estado", status_labels[workspace["status"]])
    columns[1].metric("Evidencias", len(workspace["evidence"]))
    columns[2].metric(
        "Áreas bloqueantes pendientes",
        len(workspace["missing_blocking_categories"]),
    )
    st.dataframe(coverage_rows(workspace), width="stretch")
    if workspace["documented_for_decision_review"]:
        st.success(
            "Las áreas bloqueantes están documentadas para revisión humana. "
            "Esto todavía no constituye aprobación para comprar."
        )
    else:
        st.warning(
            "La investigación sigue incompleta. Oriva mantendrá bloqueada cualquier "
            "consideración de compra."
        )


def mostrar_evidencias(st, workspace):
    st.subheader("Registro de evidencia")
    st.dataframe(evidence_rows(workspace), width="stretch")
    with st.expander("Cómo interpreta Oriva este registro"):
        st.markdown(
            "- **Dato:** información documentada en una fuente.\n"
            "- **Estimación:** aproximación que debe confirmarse.\n"
            "- **Supuesto:** valor utilizado para explorar un escenario.\n"
            "- **Documentado:** el usuario declaró haber revisado una fuente actual; "
            "no significa que Oriva la haya auditado independientemente."
        )
