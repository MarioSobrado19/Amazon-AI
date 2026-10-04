"""Piloto controlado por lote: Kroger Production -> eBay -> ORIVA."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from application.ebay_production_pipeline import run_ebay_production_pipeline
from application.production_readiness import production_readiness
from application.resale_economics import EbayFeeAssumptions
from infrastructure.ebay import EbayOpportunitySource
from infrastructure.kroger import KrogerOpportunitySource


ENGINE_VERSION = "kroger-ebay-pilot/v1"


def _gtin(value):
    normalized = re.sub(r"\D", "", str(value or ""))
    return normalized if len(normalized) in {8, 12, 13, 14} else None


def run_kroger_ebay_pilot(
    gtins, *, fee_assumptions, environ=None,
    kroger_source_factory=KrogerOpportunitySource,
    ebay_source_factory=EbayOpportunitySource,
    snapshot_directory=None,
):
    """Ejecuta 10–20 GTIN sin convertir evidencia incompleta en BUY."""
    environ = os.environ if environ is None else environ
    readiness = production_readiness(environ)
    if not readiness["ready"]:
        return {
            "status": "blocked_configuration",
            "missing": readiness["missing"],
            "results": [],
        }
    if not isinstance(fee_assumptions, EbayFeeAssumptions):
        raise TypeError("fee_assumptions debe ser EbayFeeAssumptions explícito.")
    normalized = [_gtin(value) for value in gtins]
    if any(value is None for value in normalized) or len(set(normalized)) != len(normalized):
        raise ValueError("Todos los GTIN deben ser válidos y únicos.")
    if not 10 <= len(normalized) <= 20:
        raise ValueError("El piloto debe incluir entre 10 y 20 GTIN.")

    location_id = environ["KROGER_LOCATION_ID"]
    results = []
    for gtin in normalized:
        kroger = kroger_source_factory(product_id=gtin, location_id=location_id)
        exact = [
            item for item in kroger.load()
            if _gtin(item.get("gtin")) == gtin and item.get("costo") is not None
        ]
        if len(exact) != 1 or exact[0].get("source_environment") != "production":
            results.append({
                "gtin": gtin,
                "status": "insufficient_data",
                "recommendation": "INSUFFICIENT_DATA",
                "limitations": [
                    "Kroger no devolvió un único costo Production observable para este GTIN y ubicación."
                ],
            })
            continue
        ebay = ebay_source_factory(gtin=gtin, environment="production")
        analysis = run_ebay_production_pipeline(
            gtin=gtin,
            supplier_product=exact[0],
            fee_assumptions=fee_assumptions,
            source=ebay,
        )
        results.append({
            "gtin": gtin,
            "status": analysis["status"],
            "recommendation": "INSUFFICIENT_DATA",
            "analysis": analysis,
            "limitations": [
                "No se emite BUY mientras la oportunidad permanezca commercially_unverified."
            ],
        })
    result = {
        "status": "completed",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": ENGINE_VERSION,
        "location_id": location_id,
        "count": len(results),
        "configuration": {
            "gtins": normalized,
            "fee_assumptions": fee_assumptions.__dict__.copy(),
            "ebay_environment": "production",
            "kroger_environment": "production",
        },
        "results": results,
    }
    if snapshot_directory is not None:
        result["snapshot"] = _write_snapshot(result, snapshot_directory)
    return result


def _write_snapshot(result, directory):
    """Escribe un snapshot inmutable sin credenciales ni payload OAuth."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    timestamp = result["captured_at"].replace(":", "").replace("+00:00", "Z")
    path = directory / f"{timestamp}-{digest[:12]}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {"path": str(path), "sha256": digest}


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gtin", action="append", required=True, dest="gtins")
    parser.add_argument("--snapshot-directory", default=os.getenv("ORIVA_PILOT_SNAPSHOT_DIR", "/data/pilot-snapshots"))
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
    result = run_kroger_ebay_pilot(
        args.gtins,
        fee_assumptions=assumptions,
        snapshot_directory=args.snapshot_directory,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
