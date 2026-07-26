"""Pantalla de resultados del análisis real."""

from ui.components.messages import mostrar_mensajes
from ui.navigation import CONFIGURACION, ir_a
from ui.session import limpiar_analisis, reiniciar_sesion
from ui.view_models import preparar_resultados


def _valor_o_guion(valor, formato):
    return formato.format(valor) if valor is not None else "—"


def renderizar(st, estado):
    resumen = estado["resumen"]
    resultados = estado["resultados"]

    st.title("Resultados del análisis")
    mostrar_mensajes(st, advertencias=estado.get("advertencias"))

    columnas = st.columns(4)
    columnas[0].metric("Analizados", resumen["total_analizado"])
    columnas[1].metric("Mostrados", resumen["total_mostrado"])
    columnas[2].metric(
        "Mejor ROI", _valor_o_guion(resumen["mejor_roi"], "{:.1f}%")
    )
    columnas[3].metric(
        "Mayor ganancia", _valor_o_guion(resumen["mayor_ganancia"], "${:.2f}")
    )

    if resultados:
        st.subheader("Ranking de oportunidades")
        st.dataframe(preparar_resultados(resultados), width="stretch")
        st.caption(
            f"Mejor ROI: {resumen['producto_mejor_roi']} · "
            f"Mayor ganancia: {resumen['producto_mayor_ganancia']}"
        )
    else:
        st.info("Ningún producto cumple los filtros actuales.")

    st.subheader("Distribución")
    st.write(
        f"Excelentes: **{resumen['cantidad_excelentes']}** · "
        f"Buenos: **{resumen['cantidad_buenos']}** · "
        f"Regulares: **{resumen['cantidad_regulares']}** · "
        f"No recomendados: **{resumen['cantidad_no_recomendados']}**"
    )

    ajustar, nuevo = st.columns(2)
    if ajustar.button("← Ajustar criterios"):
        limpiar_analisis(estado)
        ir_a(estado, CONFIGURACION)
        st.rerun()
    if nuevo.button("Nuevo análisis"):
        reiniciar_sesion(estado)
        st.rerun()
