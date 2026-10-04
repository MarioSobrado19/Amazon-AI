"""Gates explícitos para ejecutar el piloto eBay + Kroger en Production."""

import os


def _enabled(value):
    return str(value or "").strip().casefold() in {"1", "true", "yes"}


def production_readiness(environ=None):
    environ = os.environ if environ is None else environ
    gates = {
        "ebay_credentials": bool(environ.get("EBAY_CLIENT_ID") and environ.get("EBAY_CLIENT_SECRET")),
        "ebay_environment": environ.get("EBAY_ENVIRONMENT") == "production",
        "ebay_buy_api_production_approval": _enabled(environ.get("EBAY_BUY_PRODUCTION_APPROVED")),
        "kroger_credentials": bool(environ.get("KROGER_CLIENT_ID") and environ.get("KROGER_CLIENT_SECRET")),
        "kroger_environment": environ.get("KROGER_ENVIRONMENT") == "production",
        "kroger_production_approval": _enabled(environ.get("KROGER_PRODUCTION_APPROVED")),
        "kroger_location_id": bool(environ.get("KROGER_LOCATION_ID")),
    }
    missing = [name for name, ready in gates.items() if not ready]
    return {"ready": not missing, "gates": gates, "missing": missing}
