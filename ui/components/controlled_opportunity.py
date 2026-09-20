"""Presentación auditable del análisis controlado de una oportunidad."""


def _dinero(valor):
    return "—" if valor is None else f"${valor:,.2f}"


def _porcentaje(valor):
    return "—" if valor is None else f"{valor:.1f}%"


def filas_listings(valoracion):
    filas = []
    for listing in valoracion.get("listings", []):
        validacion = listing.get("presentation_validation", {})
        filas.append({
            "Listing": listing.get("nombre") or listing.get("ebay_item_id") or "—",
            "Precio anunciado": _dinero(listing.get("advertised_price")),
            "Envío observado": _dinero(listing.get("shipping")),
            "Precio entregado": _dinero(listing.get("delivered_price")),
            "Presentación": "Comparable" if validacion.get("accepted") else "No comparable",
            "Datos sin confirmar": ", ".join(validacion.get("unknown") or []) or "Ninguno",
            "Conflictos": ", ".join(validacion.get("conflicts") or []) or "Ninguno",
            "Atípico": "Sí" if listing.get("is_price_outlier") else "No",
        })
    return filas


def filas_escenarios(escenarios):
    filas = []
    for escenario in escenarios:
        economia = escenario.get("economics", {})
        oriva = escenario.get("oriva", {})
        listing = escenario.get("market_listing", {})
        filas.append({
            "Listing": listing.get("nombre") or listing.get("ebay_item_id") or "—",
            "Precio anunciado": _dinero(economia.get("known", {}).get("resale_price")),
            "Costo declarado": _dinero(economia.get("known", {}).get("cost")),
            "Costo total estimado": _dinero(economia.get("costo_total")),
            "Ganancia estimada": _dinero(economia.get("ganancia")),
            "Margen estimado": _porcentaje(economia.get("margen")),
            "ROI estimado": _porcentaje(economia.get("roi")),
            "Score financiero": oriva.get("opportunity_score", "—"),
            "Categoría": oriva.get("opportunity_category", "—"),
        })
    return filas


def mostrar_analisis_controlado(st, resultado):
    evidencia = resultado["pipeline_evidence"]
    valoracion = resultado["valuation"]
    st.subheader("Evidencia comercial observable")
    columnas = st.columns(4)
    columnas[0].metric("Listings observados", evidencia["active_listings_observed"])
    columnas[1].metric("GTIN confirmado", evidencia["exact_gtin_listings_accepted"])
    columnas[2].metric("Comparables útiles", valoracion["usable_comparable_count"])
    columnas[3].metric("Confianza de precio", valoracion["confidence"].capitalize())

    st.dataframe(filas_listings(valoracion), width="stretch")
    precios = valoracion["advertised_price"]
    st.caption(
        "Rango anunciado observable: "
        f"{_dinero(precios['minimum'])}–{_dinero(precios['maximum'])} · "
        f"mediana descriptiva {_dinero(precios['observable_median'])}."
    )
    if valoracion.get("representative_price") is None:
        st.warning(
            "Todavía no existe un precio representativo confiable. La mediana se muestra "
            "solo como descripción de los listings observados."
        )
    else:
        st.success(
            f"Precio representativo observable: {_dinero(valoracion['representative_price'])}."
        )

    st.subheader("Escenarios financieros por listing")
    escenarios = resultado.get("listing_scenarios") or []
    if escenarios:
        st.dataframe(filas_escenarios(escenarios), width="stretch")
    else:
        st.info("No hay listings comparables suficientes para mostrar escenarios financieros.")

    st.subheader("Qué falta antes de considerar una decisión")
    for dato in resultado["research_readiness"]["missing"]:
        st.write(f"• {dato}")
    st.error(
        "Estado: análisis financiero estimado, comercialmente no verificado. "
        "No autoriza comprar inventario ni invertir."
    )
