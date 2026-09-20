"""Expediente auditable construido exclusivamente con resultados existentes."""

from datetime import datetime, timezone
import hashlib
import json


DOSSIER_VERSION = "oriva-opportunity-dossier/1.0"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _identity_payload(pipeline_result):
    valuation = pipeline_result["valuation"]
    scenarios = pipeline_result.get("listing_scenarios") or []
    listings = [
        {
            "listing_id": item.get("ebay_item_id"),
            "observed_at": item.get("observed_at"),
            "advertised_price": item.get("advertised_price"),
        }
        for item in valuation.get("listings", [])
    ]
    assumptions = [
        scenario.get("economics", {}).get("assumptions", {})
        for scenario in scenarios
    ]
    return {
        "gtin": pipeline_result["pipeline_evidence"]["gtin"],
        "listings": sorted(listings, key=_canonical),
        "assumptions": sorted(assumptions, key=_canonical),
        "manual_cost": pipeline_result["supplier_product"].get("costo"),
        "version": DOSSIER_VERSION,
    }


def _financial_scenario(scenario):
    economics = scenario.get("economics", {})
    oriva = scenario.get("oriva", {})
    listing = scenario.get("market_listing", {})
    return {
        "listing_id": listing.get("ebay_item_id"),
        "title": listing.get("nombre"),
        "advertised_price": economics.get("known", {}).get("resale_price"),
        "declared_cost": economics.get("known", {}).get("cost"),
        "estimated_total_cost": economics.get("costo_total"),
        "estimated_profit": economics.get("ganancia"),
        "estimated_margin": economics.get("margen"),
        "estimated_roi": economics.get("roi"),
        "financial_score": oriva.get("opportunity_score"),
        "financial_category": oriva.get("opportunity_category"),
        "assumptions": dict(economics.get("assumptions", {})),
        "evidence_interpretation": (
            "Escenario financiero estimado con precio anunciado y supuestos "
            "de costos; no representa una venta confirmada."
        ),
    }


def crear_expediente_oportunidad(pipeline_result, *, generated_at=None):
    """Agrupa evidencia existente sin recalcular ni recomendar una compra."""
    if not isinstance(pipeline_result, dict):
        raise ValueError("El resultado del pipeline debe ser un objeto válido.")
    required = {"pipeline_evidence", "supplier_product", "valuation", "research_readiness"}
    if not required.issubset(pipeline_result):
        raise ValueError("El resultado del pipeline está incompleto.")

    generated_at = generated_at or datetime.now(timezone.utc)
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generated_at debe incluir zona horaria.")

    identity = _identity_payload(pipeline_result)
    dossier_id = hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest()
    evidence = pipeline_result["pipeline_evidence"]
    valuation = pipeline_result["valuation"]
    supplier = pipeline_result["supplier_product"]
    scenarios = tuple(
        _financial_scenario(item)
        for item in pipeline_result.get("listing_scenarios") or []
    )
    missing = tuple(dict.fromkeys(pipeline_result["research_readiness"].get("missing") or ()))

    observed = (
        {
            "field": "active_listings",
            "value": evidence.get("active_listings_observed"),
            "source": "ebay_browse",
            "evidence_type": "DATA",
            "meaning": "Listings activos devueltos por eBay para la consulta.",
        },
        {
            "field": "exact_gtin_matches",
            "value": evidence.get("exact_gtin_listings_accepted"),
            "source": "ebay_item_detail",
            "evidence_type": "DATA",
            "meaning": "Listings cuyo detalle confirmó exactamente el GTIN.",
        },
        {
            "field": "observable_advertised_price_range",
            "value": dict(valuation.get("advertised_price", {})),
            "source": "ebay_browse",
            "evidence_type": "DATA",
            "meaning": "Precios anunciados observables; no ventas completadas.",
        },
    )
    assumptions = (
        {
            "field": "purchase_cost",
            "value": supplier.get("costo"),
            "source": supplier.get("source", "manual_controlled_validation"),
            "evidence_type": "ASSUMPTION",
            "meaning": "Costo declarado para modelar escenarios; no cotización de proveedor.",
        },
        {
            "field": "financial_cost_assumptions",
            "value": scenarios[0]["assumptions"] if scenarios else {},
            "source": "user_declared_inputs",
            "evidence_type": "ASSUMPTION",
            "meaning": "Tarifas y costos usados para la estimación financiera.",
        },
    )

    if not scenarios:
        status = "insufficient_comparable_evidence"
        headline = "Todavía no hay escenarios financieros comparables"
    elif missing:
        status = "investigate"
        headline = "La señal financiera requiere investigación comercial"
    else:
        # En V1 la ausencia de missing no habilita una compra automática.
        status = "investigate"
        headline = "La evidencia disponible permite continuar investigando"

    return {
        "dossier_id": dossier_id,
        "version": DOSSIER_VERSION,
        "generated_at": generated_at.isoformat(),
        "product": {
            "gtin": evidence.get("gtin"),
            "identity_status": "exact_gtin_checked",
        },
        "market": {
            "marketplace": "EBAY_US",
            "environment": evidence.get("ebay_environment"),
            "active_listings_observed": evidence.get("active_listings_observed"),
            "exact_gtin_matches": evidence.get("exact_gtin_listings_accepted"),
            "usable_comparables": valuation.get("usable_comparable_count"),
            "price_confidence": valuation.get("confidence"),
            "representative_price": valuation.get("representative_price"),
        },
        "evidence": {
            "observed": observed,
            "assumptions": assumptions,
            "unknown": missing,
        },
        "financial_scenarios": scenarios,
        "guidance": {
            "state": status,
            "headline": headline,
            "why": (
                "Oriva confirmó oferta activa y calculó escenarios financieros, "
                "pero todavía faltan señales comerciales esenciales."
            ),
            "next_step": (
                "Verificar demanda, proveedor, costo final, restricciones e historial "
                "antes de considerar cualquier prueba controlada."
            ),
            "human_decision_required": True,
            "purchase_authorized": False,
        },
        "limitations": (
            "Un listing activo no es una venta confirmada.",
            "El costo declarado no es una cotización verificable de proveedor.",
            "El score es una evaluación financiera estimada, no una probabilidad de éxito.",
            "El expediente no garantiza demanda, ventas ni rentabilidad.",
            "El expediente no autoriza comprar inventario ni invertir.",
        ),
    }


def exportar_expediente_json(dossier):
    if not isinstance(dossier, dict) or not dossier.get("dossier_id"):
        raise ValueError("El expediente es inválido.")
    return {
        "nombre_archivo": f"oriva_oportunidad_{dossier['product']['gtin']}.json",
        "contenido": (json.dumps(dossier, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        "mime": "application/json",
    }


def exportar_expediente_txt(dossier):
    if not isinstance(dossier, dict) or not dossier.get("dossier_id"):
        raise ValueError("El expediente es inválido.")
    market = dossier["market"]
    guidance = dossier["guidance"]
    lines = [
        "ORIVA — EXPEDIENTE DE OPORTUNIDAD",
        "=" * 44,
        f"ID: {dossier['dossier_id']}",
        f"Fecha: {dossier['generated_at']}",
        f"GTIN: {dossier['product']['gtin']}",
        f"Marketplace: {market['marketplace']}",
        "",
        "SITUACIÓN ACTUAL",
        guidance["headline"],
        guidance["why"],
        "",
        "EVIDENCIA OBSERVADA",
        f"Listings activos: {market['active_listings_observed']}",
        f"GTIN confirmados: {market['exact_gtin_matches']}",
        f"Comparables útiles: {market['usable_comparables']}",
        f"Confianza del precio: {market['price_confidence']}",
        "",
        "DATOS FALTANTES",
        *(f"- {item}" for item in dossier["evidence"]["unknown"]),
        "",
        "SIGUIENTE PASO",
        guidance["next_step"],
        "",
        "LIMITACIONES",
        *(f"- {item}" for item in dossier["limitations"]),
        "",
        "No autoriza comprar inventario ni invertir.",
    ]
    return {
        "nombre_archivo": f"oriva_oportunidad_{dossier['product']['gtin']}.txt",
        "contenido": "\n".join(lines).encode("utf-8"),
        "mime": "text/plain",
    }
