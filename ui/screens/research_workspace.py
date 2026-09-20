"""Pantalla para documentar evidencia y evaluar cobertura de investigación."""

from datetime import datetime, timezone

from application.research_workspace_service import (
    CATEGORIES,
    agregar_evidencia,
    crear_evidencia_manual,
    eliminar_evidencia_manual,
    exportar_workspace_json,
    exportar_workspace_txt,
    importar_workspace_json,
)
from ui.components.messages import mostrar_mensajes
from ui.components.research_workspace import (
    mostrar_evidencias,
    mostrar_resumen_workspace,
)
from ui.navigation import OPORTUNIDAD_CONTROLADA, ir_a


def _evidence_form(st):
    labels = {definition["label"]: key for key, definition in CATEGORIES.items()}
    with st.form("agregar_evidencia"):
        st.subheader("Documentar nueva evidencia")
        category_label = st.selectbox("Área de investigación", tuple(labels))
        evidence_type_label = st.selectbox(
            "Tipo de información", ("Dato documentado", "Estimación", "Supuesto")
        )
        type_map = {
            "Dato documentado": "data",
            "Estimación": "estimate",
            "Supuesto": "assumption",
        }
        summary = st.text_area(
            "¿Qué indica la evidencia?",
            placeholder="Describe solo lo que la fuente permite afirmar.",
        )
        source_name = st.text_input("Nombre de la fuente")
        source_reference = st.text_input(
            "Enlace de la fuente",
            placeholder="https://...",
            help="No incluyas enlaces con tokens, claves o información privada.",
        )
        dates = st.columns(2)
        observed_at = dates[0].date_input("Fecha observada")
        has_expiration = dates[1].checkbox("Tiene fecha de vencimiento")
        valid_until = dates[1].date_input("Vigente hasta", disabled=not has_expiration)
        confidence_label = st.selectbox("Confianza declarada", ("Baja", "Media", "Alta"))
        reviewed = st.checkbox(
            "Revisé personalmente la fuente enlazada",
            help="Es una declaración humana; Oriva no audita automáticamente la fuente.",
        )
        limitations = st.text_area(
            "Limitaciones conocidas (opcional)",
            placeholder="Una limitación por línea.",
        )
        submitted = st.form_submit_button("Agregar al expediente", type="primary")
    if not submitted:
        return None
    return {
        "category": labels[category_label],
        "summary": summary,
        "evidence_type": type_map[evidence_type_label],
        "source_name": source_name or None,
        "source_reference": source_reference or None,
        "observed_at": observed_at,
        "valid_until": valid_until if has_expiration else None,
        "confidence": {"Baja": "low", "Media": "medium", "Alta": "high"}[confidence_label],
        "source_reviewed_by_user": reviewed,
        "limitations": tuple(line.strip() for line in limitations.splitlines() if line.strip()),
    }


def renderizar(st, estado):
    st.title("Research Workspace")
    st.write(
        "Reúne aquí la evidencia necesaria antes de considerar cualquier decisión. "
        "Oriva distingue datos, estimaciones, supuestos y vigencia."
    )
    workspace = estado.get("research_workspace")
    if not workspace:
        st.error("Primero debes crear un expediente de oportunidad.")
        if st.button("← Volver al análisis"):
            ir_a(estado, OPORTUNIDAD_CONTROLADA)
            st.rerun()
        return

    mostrar_resumen_workspace(st, workspace)
    mostrar_evidencias(st, workspace)
    with st.expander("Restaurar evidencia desde un respaldo"):
        st.caption(
            "Solo se importará evidencia manual del mismo expediente. "
            "La evidencia del sistema se reconstruye desde el análisis actual."
        )
        backup = st.file_uploader(
            "Selecciona un archivo JSON de Research Workspace",
            type=["json"],
            key="research_workspace_backup",
        )
        if backup is not None and st.button("Restaurar respaldo"):
            try:
                estado["research_workspace"] = importar_workspace_json(
                    backup.getvalue(),
                    workspace,
                    imported_at=datetime.now(timezone.utc),
                )
                estado["research_workspace_error"] = []
                st.rerun()
            except ValueError as error:
                estado["research_workspace_error"] = [str(error)]
    form_data = _evidence_form(st)
    if form_data is not None:
        try:
            evidence = crear_evidencia_manual(**form_data)
            estado["research_workspace"] = agregar_evidencia(
                workspace, evidence, updated_at=datetime.now(timezone.utc)
            )
            estado["research_workspace_error"] = []
            st.rerun()
        except ValueError as error:
            estado["research_workspace_error"] = [str(error)]

    manual = [item for item in workspace["evidence"] if item["origin"] == "user_declared"]
    if manual:
        with st.expander("Eliminar evidencia añadida manualmente"):
            options = {
                f"{item['category']} · {item['summary'][:60]} · {item['evidence_id'][:8]}": item["evidence_id"]
                for item in manual
            }
            selected = st.selectbox("Evidencia", tuple(options))
            if st.button("Eliminar evidencia seleccionada"):
                estado["research_workspace"] = eliminar_evidencia_manual(
                    workspace,
                    options[selected],
                    updated_at=datetime.now(timezone.utc),
                )
                st.rerun()

    mostrar_mensajes(st, estado.get("research_workspace_error"), workspace.get("warnings"))
    export = exportar_workspace_json(workspace)
    text_export = exportar_workspace_txt(workspace)
    downloads = st.columns(2)
    downloads[0].download_button(
        "Descargar investigación JSON",
        data=export["contenido"],
        file_name=export["nombre_archivo"],
        mime=export["mime"],
    )
    downloads[1].download_button(
        "Descargar resumen TXT",
        data=text_export["contenido"],
        file_name=text_export["nombre_archivo"],
        mime=text_export["mime"],
    )
    if st.button("← Volver al análisis"):
        ir_a(estado, OPORTUNIDAD_CONTROLADA)
        st.rerun()
