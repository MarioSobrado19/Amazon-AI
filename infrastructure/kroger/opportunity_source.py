"""Fuente oficial Kroger Products Public con precios ligados a una ubicación."""

from datetime import datetime, timezone
import os

from infrastructure.oauth_client import (
    ApiError,
    ClientCredentialsTokenProvider,
    default_transport,
)


class KrogerOpportunitySource:
    source_id = "kroger_products_public"
    scope = "product.compact"

    def __init__(
        self, *, product_id, location_id, limit=10, environment=None,
        client_id=None, client_secret=None, base_url=None,
        transport=default_transport, clock=None
    ):
        if not str(product_id or "").strip():
            raise ValueError("Kroger requiere product_id/UPC.")
        if not str(location_id or "").strip():
            raise ValueError("Kroger requiere locationId para observar precios.")
        self.product_id = str(product_id).strip()
        self.location_id = str(location_id).strip()
        self.limit = min(max(int(limit), 1), 50)
        self.environment = environment or os.getenv("KROGER_ENVIRONMENT", "certification")
        self.base_url = (base_url or os.getenv("KROGER_BASE_URL", "https://api.kroger.com/v1")).rstrip("/")
        kwargs = {"transport": transport}
        if clock is not None:
            kwargs["clock"] = clock
        self.tokens = ClientCredentialsTokenProvider(
            f"{self.base_url}/connect/oauth2/token",
            client_id or os.getenv("KROGER_CLIENT_ID"),
            client_secret or os.getenv("KROGER_CLIENT_SECRET"),
            self.scope,
            **kwargs,
        )
        self.transport = transport

    def load(self):
        token = self.tokens.get_token()
        _, headers, payload = self.transport(
            "GET",
            f"{self.base_url}/products",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params={
                "filter.productId": self.product_id,
                "filter.locationId": self.location_id,
                "filter.limit": self.limit,
            },
        )
        if not isinstance(payload, dict):
            raise ApiError("invalid_response", "Kroger devolvió una respuesta inválida.")
        observed_at = datetime.now(timezone.utc).isoformat()
        results = []
        for product in payload.get("data") or []:
            for item in product.get("items") or [{}]:
                price = item.get("price") or {}
                value = price.get("promo") or price.get("regular")
                try:
                    value = float(value) if value is not None else None
                except (TypeError, ValueError):
                    value = None
                results.append({
                    "nombre": product.get("description"),
                    "gtin": product.get("upc"),
                    "costo": value,
                    "kroger_product_id": product.get("productId"),
                    "brand": product.get("brand"),
                    "size": item.get("size"),
                    "location_id": self.location_id,
                    "source": self.source_id,
                    "source_environment": self.environment,
                    "observed_at": observed_at,
                    "evidence_status": "observed" if value is not None else "unknown",
                    "limitations": [
                        "El precio depende de la ubicación y puede cambiar sin previo aviso.",
                        *(
                            ["Certification no acredita disponibilidad ni precios de producción."]
                            if self.environment == "certification" else []
                        ),
                    ],
                    "rate_limit": {
                        key: header_value for key, header_value in headers.items()
                        if "rate" in key.casefold()
                    },
                })
        return results
