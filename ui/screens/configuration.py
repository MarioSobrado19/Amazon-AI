"""Pantalla para configurar y ejecutar el análisis."""

from application import (
    CONFIGURACION_PREDETERMINADA,
    analizar,
    crear_dashboard,
    generar_decision,
    generar_insights,
)
from ui.components.messages import mostrar_mensajes
from ui.components.progress import mostrar_progreso
from ui.navigation import CONFIGURACION, RESULTADOS, VISTA_PREVIA, ir_a
from ui.session import guardar_analisis
from ui.view_models import (
    construir_filtros,
    mensajes_de_error,
    preparar_estado_filtros,
)


def _filtros_desde_formulario(st, filtros_guardados):
    inicial = preparar_estado_filtros(filtros_guardados)
    controles = (
        ("roi_minimo", "ROI mínimo (%)"),
        ("margen_minimo", "Margen mínimo (%)"),
        ("ganancia_minima", "Ganancia mínima ($)"),
        ("precio_maximo", "Precio máximo ($)"),
    )
    activos = {}
    valores = {}

    for clave, etiqueta in controles:
        columna_activa, columna_valor = st.columns([1, 2])
        activos[clave] = columna_activa.checkbox(
            "Aplicar",
            value=inicial["activos"][clave],
            key=f"activar_{clave}",
        )
        valores[clave] = columna_valor.number_input(
            etiqueta,
            min_value=0.0,
            value=inicial["valores"][clave],
            key=f"valor_{clave}",
        )

    texto = st.text_input(
        "Buscar en el nombre (opcional)",
        value=inicial["texto_nombre"],
    )
    return construir_filtros(
        {"activos": activos, "valores": valores, "texto_nombre": texto}
    )


def renderizar(st, estado):
    mostrar_progreso(st, CONFIGURACION)
    st.title("Configura el análisis")
    st.write(f"Analizarás **{estado['total_productos']} productos**.")

    valores = estado.get("configuracion") or CONFIGURACION_PREDETERMINADA
    st.subheader("Costos estimados por producto")
    envio = st.number_input(
        "Envío ($)", min_value=0.0, value=float(valores["envio_predeterminado"])
    )
    tarifa = st.number_input(
        "Tarifa de Amazon (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(valores["tarifa_amazon_porcentaje"] * 100),
    )
    otros = st.number_input(
        "Otros costos ($)",
        min_value=0.0,
        value=float(valores["otros_costos_predeterminados"]),
    )

    with st.expander("Niveles de evaluación por ROI"):
        st.caption("Puedes conservar estos valores recomendados para comenzar.")
        roi_excelente = st.number_input(
            "Excelente desde (%)",
            min_value=0.0,
            value=float(valores["roi_excelente"]),
        )
        roi_bueno = st.number_input(
            "Bueno desde (%)", min_value=0.0, value=float(valores["roi_bueno"])
        )
        roi_regular = st.number_input(
            "Regular desde (%)",
            min_value=0.0,
            value=float(valores["roi_regular"]),
        )

    st.subheader("Filtros opcionales")
    st.caption("Activa únicamente los filtros que quieras aplicar.")
    filtros = _filtros_desde_formulario(st, estado.get("filtros"))
    ejecutar = st.button("Analizar productos", type="primary")

    if ejecutar:
        configuracion = {
            "envio_predeterminado": envio,
            "tarifa_amazon_porcentaje": tarifa / 100,
            "otros_costos_predeterminados": otros,
            "roi_excelente": roi_excelente,
            "roi_bueno": roi_bueno,
            "roi_regular": roi_regular,
        }
        with st.spinner("Calculando rentabilidad y preparando el ranking..."):
            resultado = analizar(estado["productos"], filtros, configuracion)
        if resultado["exito"]:
            datos = resultado["datos"]
            resumen = crear_dashboard(
                datos["resultados"], datos["total_analizado"]
            )
            if resumen["exito"]:
                insights = generar_insights(
                    datos["resultados_completos"],
                    datos["resultados"],
                    resumen["datos"],
                    datos["filtros_aplicados"],
                )
                if insights["exito"]:
                    decision = generar_decision(
                        datos["resultados_completos"],
                        datos["resultados"],
                        resumen["datos"],
                        insights["datos"],
                        datos["filtros_aplicados"],
                    )
                    if decision["exito"]:
                        guardar_analisis(
                            estado,
                            datos,
                            resumen["datos"],
                            insights["datos"],
                            decision["datos"],
                        )
                        estado["advertencias"] = resultado["advertencias"]
                        ir_a(estado, RESULTADOS)
                        st.rerun()
                    else:
                        estado["errores"] = mensajes_de_error(decision)
                else:
                    estado["errores"] = mensajes_de_error(insights)
            else:
                estado["errores"] = mensajes_de_error(resumen)
        else:
            estado["errores"] = mensajes_de_error(resultado)

    mostrar_mensajes(st, estado.get("errores"))
    if st.button("← Volver a revisar productos"):
        ir_a(estado, VISTA_PREVIA)
        st.rerun()
