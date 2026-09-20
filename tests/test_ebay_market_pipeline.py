import unittest

from application.market_opportunity_service import build_market_opportunities
from application.product_matching import match_products
from application.resale_economics import EbayFeeAssumptions, calculate_resale_economics
from infrastructure.ebay import EbayOpportunitySource
from infrastructure.oauth_client import ApiError, ClientCredentialsTokenProvider


class FakeTransport:
    def __init__(self, api_payload, api_headers=None):
        self.api_payload = api_payload
        self.api_headers = api_headers or {}
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if "oauth2/token" in url:
            return 200, {}, {"access_token": "test-token", "expires_in": 3600}
        return 200, self.api_headers, self.api_payload


class OAuthTests(unittest.TestCase):
    def test_cachea_token_y_no_expone_secret_en_representacion(self):
        transport = FakeTransport({})
        provider = ClientCredentialsTokenProvider(
            "https://example.test/oauth2/token",
            "test-id",
            "test-secret",
            "scope",
            transport=transport,
            clock=lambda: 100,
        )

        self.assertEqual(provider.get_token(), "test-token")
        self.assertEqual(provider.get_token(), "test-token")
        self.assertEqual(len(transport.calls), 1)
        self.assertNotIn("test-secret", repr(provider))

    def test_rechaza_respuesta_sin_token(self):
        transport = lambda *args, **kwargs: (200, {}, {})
        provider = ClientCredentialsTokenProvider(
            "https://example.test/token", "test-id", "test-secret", "scope", transport=transport
        )

        with self.assertRaisesRegex(ApiError, "access token"):
            provider.get_token()


class EbaySourceTests(unittest.TestCase):
    def test_normaliza_listings_sin_inventar_ventas(self):
        transport = FakeTransport(
            {
                "total": 42,
                "itemSummaries": [{
                    "itemId": "v1|1|0",
                    "title": "Cereal",
                    "gtin": "000123",
                    "price": {"value": "19.99", "currency": "USD"},
                    "condition": "New",
                }],
            },
            {"X-RateLimit-Remaining": "99"},
        )
        source = EbayOpportunitySource(
            gtin="000123", client_id="test-id", client_secret="test-secret", transport=transport
        )

        item = source.load()[0]

        self.assertEqual(item["precio"], 19.99)
        self.assertEqual(item["competition_listing_count"], 42)
        self.assertNotIn("sales", item)
        self.assertIn("no representan ventas", item["limitations"][0])
        self.assertEqual(transport.calls[-1][2]["params"]["gtin"], "000123")

    def test_sandbox_queda_marcado_y_sin_datos_es_lista_vacia(self):
        source = EbayOpportunitySource(
            query="cereal",
            environment="sandbox",
            client_id="test-id",
            client_secret="test-secret",
            transport=FakeTransport({"itemSummaries": []}),
        )

        self.assertEqual(source.load(), [])
        self.assertIn("sandbox", source.base_url)

    def test_propaga_rate_limit_tipado(self):
        def limited(*args, **kwargs):
            raise ApiError("rate_limited", "HTTP 429", retryable=True, status=429)

        source = EbayOpportunitySource(
            query="x", client_id="test-id", client_secret="test-secret", transport=limited
        )

        with self.assertRaises(ApiError) as raised:
            source.load()
        self.assertTrue(raised.exception.retryable)


class MatchingEconomicsAndScoringTests(unittest.TestCase):
    def test_gtin_exacto_es_alta_confianza_y_conflicto_no_match(self):
        exact = match_products({"gtin": "00123"}, {"gtin": "00123"})
        conflict = match_products({"gtin": "00123"}, {"gtin": "00999"})

        self.assertTrue(exact.matched)
        self.assertEqual(exact.confidence, "high")
        self.assertFalse(conflict.matched)

    def test_nombre_solo_no_se_presenta_como_seguro(self):
        match = match_products(
            {"nombre": "Cereal marca 12 oz"}, {"nombre": "Cereal marca 12 oz"}
        )

        self.assertFalse(match.matched)
        self.assertEqual(match.confidence, "low")

    def test_economia_separa_conocido_de_supuestos(self):
        result = calculate_resale_economics(
            5, 15, EbayFeeAssumptions(.13, fixed=.30, shipping=2)
        )

        self.assertEqual(result["known"], {"cost": 5.0, "resale_price": 15.0})
        self.assertEqual(result["assumptions"]["percentage"], .13)
        self.assertEqual(result["ganancia"], 5.75)

    def test_flujo_reutiliza_opportunity_service_oficial(self):
        supplier = {
            "nombre": "Cereal",
            "gtin": "00123",
            "costo": 5,
            "source": "manual_controlled_validation",
            "limitations": ["Costo supuesto"],
        }
        listing = {
            "nombre": "Cereal",
            "gtin": "00123",
            "precio": 15,
            "source": "ebay_browse",
            "limitations": ["Listing activo; no es una venta"],
        }

        result = build_market_opportunities(
            [supplier], [listing], EbayFeeAssumptions(.13)
        )[0]

        self.assertEqual(result["status"], "scored")
        self.assertEqual(result["match"]["confidence"], "high")
        self.assertEqual(result["oriva"]["opportunity_score"], 70.3)
        self.assertIn("opportunity_factors", result["oriva"])

    def test_sin_match_no_calcula_oportunidad(self):
        results = build_market_opportunities(
            [{"nombre": "A", "gtin": "1"}],
            [{"nombre": "B", "gtin": "2"}],
            EbayFeeAssumptions(.1),
        )

        self.assertEqual(results[0]["status"], "unmatched")


if __name__ == "__main__":
    unittest.main()
