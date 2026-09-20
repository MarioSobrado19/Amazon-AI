"""Fuente eBay Browse: listings activos observables, nunca ventas inferidas."""

import os
from urllib.parse import quote
from datetime import datetime, timezone

from infrastructure.oauth_client import ClientCredentialsTokenProvider, ApiError, default_transport


class EbayOpportunitySource:
    source_id = "ebay_browse"
    scope = "https://api.ebay.com/oauth/api_scope"

    def __init__(self, *, query=None, gtin=None, marketplace="EBAY_US", limit=20, environment=None, client_id=None, client_secret=None, transport=default_transport, clock=None):
        if not query and not gtin:
            raise ValueError("eBay requiere query o GTIN.")
        self.query, self.gtin, self.marketplace = query, gtin, marketplace
        self.limit = min(max(int(limit), 1), 200)
        self.environment = environment or os.getenv("EBAY_ENVIRONMENT", "sandbox")
        host = "api.sandbox.ebay.com" if self.environment == "sandbox" else "api.ebay.com"
        self.base_url = f"https://{host}"
        client_id = client_id or os.getenv("EBAY_CLIENT_ID")
        client_secret = client_secret or os.getenv("EBAY_CLIENT_SECRET")
        kwargs = {"transport": transport}
        if clock is not None:
            kwargs["clock"] = clock
        self.tokens = ClientCredentialsTokenProvider(f"{self.base_url}/identity/v1/oauth2/token", client_id, client_secret, self.scope, **kwargs)
        self.transport = transport

    def get_item(self, item_id):
        if not item_id:
            raise ValueError("eBay requiere item_id.")
        token = self.tokens.get_token()
        encoded_item_id = quote(str(item_id), safe="")
        _, headers, payload = self.transport(
            "GET",
            f"{self.base_url}/buy/browse/v1/item/{encoded_item_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
            },
        )
        if not isinstance(payload, dict):
            raise ApiError("invalid_response", "eBay devolvió una respuesta inválida.")
        return payload

    def load(self):
        params = {"limit": self.limit}
        params["gtin" if self.gtin else "q"] = self.gtin or self.query
        token = self.tokens.get_token()
        _, headers, payload = self.transport("GET", f"{self.base_url}/buy/browse/v1/item_summary/search", headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": self.marketplace}, params=params)
        if not isinstance(payload, dict):
            raise ApiError("invalid_response", "eBay devolvió una respuesta inválida.")
        observed_at = datetime.now(timezone.utc).isoformat()
        results = []
        for item in payload.get("itemSummaries") or []:
            price = item.get("price") or {}
            value = price.get("value")
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = None
            results.append({
                "nombre": item.get("title"), "precio": value,
                "currency": price.get("currency"), "ebay_item_id": item.get("itemId"),
                "gtin": item.get("gtin"), "condition": item.get("condition"),
                "item_url": item.get("itemWebUrl"), "marketplace_id": self.marketplace,
                "source": self.source_id, "source_environment": self.environment,
                "observed_at": observed_at, "evidence_status": "observed",
                "competition_listing_count": payload.get("total"),
                "limitations": ["Listings activos y precios anunciados; no representan ventas ni demanda."],
                "rate_limit": {key: value for key, value in headers.items() if "rate" in key.casefold()},
            })
        return results
