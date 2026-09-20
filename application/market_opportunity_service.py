"""Flujo de evidencia de costo -> listing -> economía -> Opportunity Engine."""

from datetime import datetime, timezone

from application.opportunity_service import puntuar_producto
from application.product_matching import match_products
from application.resale_economics import calculate_resale_economics


def build_market_opportunities(
    supplier_products,
    market_listings,
    fee_assumptions,
    *,
    score_product=puntuar_producto,
    history=None,
):
    results = []
    for supplier in supplier_products:
        candidates = []
        for listing in market_listings:
            match = match_products(supplier, listing)
            if match.matched:
                candidates.append((match, listing))
        if not candidates:
            results.append({"supplier_product": supplier, "status": "unmatched", "limitations": ["No se encontró una coincidencia suficientemente confiable en eBay."]})
            continue
        match, listing = max(candidates, key=lambda item: item[0].score)
        economics = calculate_resale_economics(supplier.get("costo"), listing.get("precio"), fee_assumptions)
        if economics["status"] == "unknown":
            results.append({"supplier_product": supplier, "market_listing": listing, "match": match.__dict__, "economics": economics, "status": "insufficient_data"})
            continue
        score_input = {"nombre": supplier.get("nombre"), "roi": economics["roi"], "margen": economics["margen"], "ganancia": economics["ganancia"], "source_evidence": {"cost": supplier.get("source"), "resale_price": listing.get("source"), "economics": "estimated_from_observed_inputs"}}
        score_response = score_product(score_input)
        if not score_response["exito"]:
            results.append({
                "supplier_product": supplier,
                "market_listing": listing,
                "match": match.__dict__,
                "economics": economics,
                "status": "scoring_failed",
                "errors": score_response["errores"],
            })
            continue
        scored = score_response["datos"]
        result = {"status": "scored", "supplier_product": supplier, "market_listing": listing, "match": match.__dict__, "economics": economics, "oriva": scored}
        results.append(result)
        if history:
            history.append({
                "opportunity": {"name": supplier.get("nombre"), "gtin": supplier.get("gtin")},
                "data_used": {"supplier": supplier, "market": listing, "economics": economics},
                "oriva_result": scored,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "engine_version": "opportunity-service/current",
            })
    return results
