"""Pantalla para configurar y ejecutar el análisis."""

from application import CONFIGURACION_PREDETERMINADA, analizar, resumir
from ui.components.messages import mostrar_mensajes
from ui.navigation import PRODUCTOS_LISTOS, RESULTADOS, ir_a
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

    st.subheader("Niveles de evaluación por ROI")
    roi_excelente = st.number_input(
        "Excelente desde (%)", min_value=0.0, value=float(valores["roi_excelente"])
    )
    roi_bueno = st.number_input(
        "Bueno desde (%)", min_value=0.0, value=float(valores["roi_bueno"])
    )
    roi_regular = st.number_input(
        "Regular desde (%)", min_value=0.0, value=float(valores["roi_regular"])
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
        resultado = analizar(estado["productos"], filtros, configuracion)
        if resultado["exito"]:
            datos = resultado["datos"]
            resumen = resumir(datos["resultados"], datos["total_analizado"])
            if resumen["exito"]:
                guardar_analisis(estado, datos, resumen["datos"])
                estado["advertencias"] = resultado["advertencias"]
                ir_a(estado, RESULTADOS)
                st.rerun()
            estado["errores"] = mensajes_de_error(resumen)
        else:
            estado["errores"] = mensajes_de_error(resultado)

    mostrar_mensajes(st, estado.get("errores"))
    if st.button("← Volver a productos listos"):
        ir_a(estado, PRODUCTOS_LISTOS)
        st.rerun()
