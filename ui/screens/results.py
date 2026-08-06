"""Pantalla de resultados del análisis real."""

from application import LIMITACIONES_PILOTO, exportar, generar_reporte_comercial
from ui.components.dashboard import mostrar_dashboard
from ui.components.decision import mostrar_decision
from ui.components.highlight import mostrar_mejor_producto
from ui.components.insights import mostrar_insights
from ui.components.messages import mostrar_mensajes
from ui.components.progress import mostrar_progreso
from ui.navigation import CONFIGURACION, ir_a
from ui.session import limpiar_analisis, reiniciar_sesion
from ui.view_models import mensajes_de_error, preparar_resultados


def renderizar(st, estado):
    resumen = estado["resumen"]
    resultados = estado["resultados"]

    mostrar_progreso(st, "resultados")
    st.title("Resultados del análisis")
    st.success(f"Analizamos correctamente {resumen['total_analizado']} productos.")
    mostrar_mensajes(st, advertencias=estado.get("advertencias"))

    mostrar_dashboard(st, resumen)
    if estado.get("insights"):
        mostrar_insights(st, estado["insights"])
    if estado.get("decision"):
        mostrar_decision(st, estado["decision"])

    if resultados:
        mostrar_mejor_producto(st, resumen["producto_destacado"])
        st.subheader("Ranking de oportunidades")
        st.dataframe(preparar_resultados(resultados), width="stretch")
        with st.expander("¿Qué significan estos indicadores?"):
            st.markdown(
                "- **ROI:** rendimiento estimado frente al costo base del producto.\n"
                "- **Margen:** porcentaje del precio que queda como ganancia estimada.\n"
                "- **Ganancia:** dinero estimado restante después de los costos configurados."
            )

        st.subheader("Descargar resultados")
        reporte_comercial = generar_reporte_comercial(
            resultados,
            resumen,
            estado.get("insights", {}),
        )
        exportacion_csv = exportar(resultados, "csv")
        exportacion_txt = exportar(resultados, "txt")
        errores_exportacion = []
        descargas = st.columns(3)
        if reporte_comercial["exito"]:
            datos_comerciales = reporte_comercial["datos"]
            descargas[0].download_button(
                "Descargar reporte comercial",
                data=datos_comerciales["contenido"],
                file_name=datos_comerciales["nombre_archivo"],
                mime="text/plain",
                type="primary",
            )
        if exportacion_csv["exito"]:
            datos_csv = exportacion_csv["datos"]
            descargas[1].download_button(
                "Descargar CSV",
                data=datos_csv["contenido"],
                file_name=datos_csv["nombre_archivo"],
                mime="text/csv",
            )
        if exportacion_txt["exito"]:
            datos_txt = exportacion_txt["datos"]
            descargas[2].download_button(
                "Descargar TXT",
                data=datos_txt["contenido"],
                file_name=datos_txt["nombre_archivo"],
                mime="text/plain",
            )
        for exportacion in (reporte_comercial, exportacion_csv, exportacion_txt):
            if not exportacion["exito"]:
                errores_exportacion.extend(mensajes_de_error(exportacion))
        mostrar_mensajes(st, errores=errores_exportacion)
        with st.expander("Uso responsable y limitaciones"):
            st.warning(LIMITACIONES_PILOTO)
            st.write(
                "Confirma costos, demanda, competencia y condiciones del marketplace "
                "antes de invertir. El score financiero no garantiza ventas."
            )
    else:
        st.info("Ningún producto cumple los filtros actuales.")

    ajustar, nuevo = st.columns(2)
    if ajustar.button("← Ajustar criterios"):
        limpiar_analisis(estado)
        ir_a(estado, CONFIGURACION)
        st.rerun()
    if nuevo.button("Nuevo análisis"):
        reiniciar_sesion(estado)
        st.rerun()
