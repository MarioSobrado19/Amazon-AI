"""Flujo visual GTIN -> eBay -> valoración -> escenarios controlados."""

from application.controlled_opportunity_service import (
    analizar_oportunidad_controlada,
    estado_conexion_ebay,
)
from ui.components.controlled_opportunity import mostrar_analisis_controlado
from ui.components.messages import mostrar_mensajes
from ui.navigation import BIENVENIDA, ir_a


def _campo_costos(st):
    st.subheader("Supuestos controlados")
    st.caption(
        "Estos valores los declaras tú. Oriva no los presenta como costos oficiales "
        "de eBay ni como cotización de un proveedor."
    )
    costo = st.number_input("Costo de compra por unidad ($)", min_value=0.01, value=8.00)
    columnas = st.columns(2)
    porcentaje = columnas[0].number_input(
        "Tarifa porcentual asumida (%)", min_value=0.0, max_value=100.0, value=13.6
    )
    fija = columnas[1].number_input("Tarifa fija asumida ($)", min_value=0.0, value=0.40)
    envio = columnas[0].number_input("Envío asumido ($)", min_value=0.0, value=5.00)
    empaque = columnas[1].number_input("Empaque asumido ($)", min_value=0.0, value=0.50)
    with st.expander("Otros supuestos"):
        impuesto = st.number_input("Impuesto de compra asumido ($)", min_value=0.0, value=0.0)
        promocion = st.number_input(
            "Promoción asumida (%)", min_value=0.0, max_value=100.0, value=0.0
        )
        otros = st.number_input("Otros costos asumidos ($)", min_value=0.0, value=0.0)
    return {
        "costo_manual": costo,
        "tarifa_porcentaje": porcentaje,
        "tarifa_fija": fija,
        "envio": envio,
        "impuesto_compra": impuesto,
        "empaque": empaque,
        "promocion_porcentaje": promocion,
        "otros": otros,
    }


def renderizar(st, estado):
    st.title("Analiza una oportunidad observada en eBay")
    st.write(
        "Introduce un GTIN y un costo controlado. Oriva buscará listings activos, "
        "confirmará la identidad del producto y mostrará escenarios financieros."
    )
    st.info(
        "Este análisis observa oferta publicada. No confirma ventas, demanda, "
        "proveedor, disponibilidad futura ni rentabilidad."
    )

    conexion = estado_conexion_ebay()
    if not conexion["ready"]:
        st.error("La conexión eBay Production no está disponible en este entorno.")
        faltantes = []
        if not conexion["credentials_configured"]:
            faltantes.append("credenciales locales")
        if conexion["environment"] != "production":
            faltantes.append("EBAY_ENVIRONMENT=production")
        if not conexion["production_approved"]:
            faltantes.append("confirmación EBAY_BUY_PRODUCTION_APPROVED=true")
        st.caption("Falta: " + ", ".join(faltantes) + ". No pegues secretos en la interfaz.")

    gtin = st.text_input(
        "GTIN / UPC / EAN",
        placeholder="Ejemplo: 629721670295",
        help="Usamos el identificador para confirmar cada listing mediante su detalle.",
    )
    valores = _campo_costos(st)
    analizar = st.button(
        "Consultar eBay y analizar",
        type="primary",
        disabled=not conexion["ready"],
    )
    if analizar:
        with st.spinner("Consultando eBay y validando listings uno por uno..."):
            respuesta = analizar_oportunidad_controlada(gtin=gtin, **valores)
        if respuesta["exito"]:
            estado["oportunidad_controlada"] = respuesta["datos"]
            estado["oportunidad_advertencias"] = respuesta["advertencias"]
            estado["oportunidad_errores"] = []
        else:
            estado["oportunidad_controlada"] = None
            estado["oportunidad_advertencias"] = []
            estado["oportunidad_errores"] = [
                error["mensaje"] for error in respuesta["errores"]
            ]

    mostrar_mensajes(
        st,
        estado.get("oportunidad_errores"),
        estado.get("oportunidad_advertencias"),
    )
    if estado.get("oportunidad_controlada"):
        mostrar_analisis_controlado(st, estado["oportunidad_controlada"])

    if st.button("← Volver al inicio"):
        ir_a(estado, BIENVENIDA)
        st.rerun()
