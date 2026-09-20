"""Ejecución controlada GTIN -> eBay Browse -> economía -> Oriva.

Los resultados de Browse son listings activos observados, no ventas. El costo
lo aporta quien ejecuta el pipeline y nunca se presenta como costo de proveedor.
"""

import argparse
import json
import re

from application.market_opportunity_service import build_market_opportunities
from application.listing_valuation import extract_presentation, extract_shipping, value_listings
from application.resale_economics import EbayFeeAssumptions
from infrastructure.ebay import EbayOpportunitySource
from infrastructure.oauth_client import ApiError


GTIN_ASPECT_NAMES = {"ean", "gtin", "isbn", "upc"}


def _digits(value):
    return re.sub(r"\D", "", str(value or ""))


def _detail_gtin(detail):
    direct = _digits(detail.get("gtin"))
    if direct:
        return direct
    for aspect in detail.get("localizedAspects") or []:
        if str(aspect.get("name", "")).strip().casefold() in GTIN_ASPECT_NAMES:
            value = _digits(aspect.get("value"))
            if value:
                return value
    return None


def run_ebay_production_pipeline(*, gtin, manual_cost, fee_assumptions, source=None, minimum_comparables=3):
    """Ejecuta el pipeline sin persistir datos ni inferir demanda o ventas."""
    gtin = _digits(gtin)
    if not gtin:
        raise ValueError("Se requiere un GTIN válido.")
    if manual_cost is None or float(manual_cost) <= 0:
        raise ValueError("El costo manual/controlado debe ser mayor que cero.")
    if not isinstance(fee_assumptions, EbayFeeAssumptions):
        raise TypeError("fee_assumptions debe ser EbayFeeAssumptions explícito.")

    source = source or EbayOpportunitySource(gtin=gtin, environment="production")
    summaries = source.load()
    identity_matches = []
    rejected_details = 0
    detail_errors = 0
    for summary in summaries:
        item_id = summary.get("ebay_item_id")
        if not item_id:
            continue
        try:
            detail = source.get_item(item_id)
        except ApiError:
            detail_errors += 1
            continue
        observed_gtin = _detail_gtin(detail)
        if observed_gtin != gtin:
            rejected_details += 1
            continue
        advertised_price = summary.get("precio")
        if advertised_price is None:
            rejected_details += 1
            continue
        shipping = extract_shipping(detail)
        listing = dict(summary)
        listing["gtin"] = observed_gtin
        listing["nombre"] = detail.get("title") or listing.get("nombre")
        listing["condition"] = detail.get("condition") or listing.get("condition")
        listing["detail_evidence_status"] = "observed"
        identity_matches.append({
            **listing,
            "identity_validation": {"gtin": "exact", "state": "identity_matched"},
            "advertised_price": float(advertised_price),
            "shipping": shipping,
            "delivered_price": round(float(advertised_price) + shipping, 2) if shipping is not None else None,
            "presentation": extract_presentation(detail, listing),
        })

    valuation = value_listings(identity_matches, minimum_comparables=minimum_comparables)
    comparable_listings = [
        item for item in valuation["listings"]
        if item["presentation_validation"]["accepted"] and not item.get("is_price_outlier")
    ]

    supplier_input = {
        "nombre": f"Controlled validation input {gtin}",
        "gtin": gtin,
        "costo": float(manual_cost),
        "source": "manual_controlled_validation",
        "evidence_status": "ASSUMPTION",
        "limitations": [
            "El costo es un input manual/controlado para validar el pipeline; no fue obtenido de un proveedor.",
        ],
    }
    scenarios = []
    for listing in comparable_listings:
        scenario = build_market_opportunities(
            [supplier_input], [{**listing, "precio": listing["advertised_price"]}], fee_assumptions
        )[0]
        if scenario["status"] == "scored":
            scenarios.append(scenario)
    achieved = ["observed"] if summaries else []
    if identity_matches:
        achieved.append("identity_matched")
    if scenarios:
        achieved.append("financially_scored")
    achieved.append("commercially_unverified")
    research_missing = [
        "ventas completadas o señal legítima de demanda",
        "proveedor y costo verificables",
        "validación de disponibilidad",
        "historial temporal",
        "restricciones aplicables",
    ]
    if valuation["representative_price"] is None:
        research_missing.append("precio representativo confiable")
    if valuation["usable_comparable_count"] < minimum_comparables:
        research_missing.append("competencia suficiente")
    result = {
        "status": "financially_scored" if scenarios else "commercially_unverified",
        "commercial_status": "commercially_unverified",
        "states": {
            "achieved": achieved,
            "current": (["financially_scored", "commercially_unverified"] if scenarios else ["commercially_unverified"]),
            "research_ready": False,
        },
        "supplier_product": supplier_input,
        "valuation": valuation,
        "listing_scenarios": scenarios,
        "research_readiness": {
            "status": "not_ready",
            "missing": research_missing,
        },
    }
    result["pipeline_evidence"] = {
        "gtin": gtin,
        "ebay_environment": getattr(source, "environment", "production"),
        "active_listings_observed": len(summaries),
        "exact_gtin_listings_accepted": len(identity_matches),
        "presentation_comparables_accepted": valuation["comparable_count"],
        "listing_details_rejected": rejected_details,
        "listing_detail_errors": detail_errors,
        "price_interpretation": "Precio anunciado de un listing activo observado; no es una venta confirmada.",
        "cost_interpretation": "Costo manual/controlado de validación; no es un costo real de proveedor.",
    }
    return result


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gtin", required=True)
    parser.add_argument("--manual-cost", required=True, type=float)
    parser.add_argument("--fee-percentage", required=True, type=float)
    parser.add_argument("--fee-fixed", required=True, type=float)
    parser.add_argument("--shipping", required=True, type=float)
    parser.add_argument("--acquisition-sales-tax", required=True, type=float)
    parser.add_argument("--packaging", required=True, type=float)
    parser.add_argument("--promotion-percentage", required=True, type=float)
    parser.add_argument("--other", required=True, type=float)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    assumptions = EbayFeeAssumptions(
        percentage=args.fee_percentage,
        fixed=args.fee_fixed,
        shipping=args.shipping,
        acquisition_sales_tax=args.acquisition_sales_tax,
        packaging=args.packaging,
        promotion_percentage=args.promotion_percentage,
        other=args.other,
    )
    result = run_ebay_production_pipeline(
        gtin=args.gtin,
        manual_cost=args.manual_cost,
        fee_assumptions=assumptions,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
