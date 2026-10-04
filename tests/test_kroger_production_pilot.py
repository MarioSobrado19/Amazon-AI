import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from application.kroger_ebay_pilot import run_kroger_ebay_pilot
from application.production_readiness import production_readiness
from application.resale_economics import EbayFeeAssumptions
from infrastructure.kroger import KrogerOpportunitySource


READY = {
    "EBAY_CLIENT_ID": "test-id",
    "EBAY_CLIENT_SECRET": "test-secret",
    "EBAY_ENVIRONMENT": "production",
    "EBAY_BUY_PRODUCTION_APPROVED": "true",
    "KROGER_CLIENT_ID": "test-id",
    "KROGER_CLIENT_SECRET": "test-secret",
    "KROGER_ENVIRONMENT": "production",
    "KROGER_PRODUCTION_APPROVED": "true",
    "KROGER_LOCATION_ID": "01400943",
}


class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if "oauth2/token" in url:
            return 200, {}, {"access_token": "test-token", "expires_in": 3600}
        return 200, {"X-RateLimit-Remaining": "9"}, self.payload


class FakeKrogerSource:
    def __init__(self, *, product_id, location_id):
        self.product_id = product_id
        self.location_id = location_id

    def load(self):
        return [{
            "nombre": "Coffee pods 48 ct",
            "gtin": self.product_id,
            "costo": 8.0,
            "brand": "Great Value",
            "size": "48 ct",
            "source": "kroger_products_public",
            "source_environment": "production",
            "evidence_status": "observed",
            "location_id": self.location_id,
            "limitations": [],
        }]


class FakeEbaySource:
    environment = "production"

    def __init__(self, *, gtin, environment):
        self.gtin = gtin

    def load(self):
        return [{
            "nombre": "Coffee pods 48 ct",
            "precio": 20.0,
            "currency": "USD",
            "condition": "New",
            "ebay_item_id": f"v1|{self.gtin}|0",
            "source": "ebay_browse",
            "evidence_status": "observed",
            "limitations": ["Listing activo; no es venta."],
        }]

    def get_item(self, item_id):
        return {
            "gtin": self.gtin,
            "title": "Coffee pods 48 ct",
            "condition": "New",
            "localizedAspects": [{"name": "Brand", "value": "Great Value"}],
            "shippingOptions": [{"shippingCost": {"value": "0"}}],
        }


class KrogerSourceTests(unittest.TestCase):
    def test_normaliza_precio_production_ligado_a_ubicacion(self):
        transport = FakeTransport({"data": [{
            "productId": "p1", "upc": "000123456789", "description": "Coffee",
            "brand": "Brand", "items": [{"size": "12 oz", "price": {"regular": 9.99}}],
        }]})
        source = KrogerOpportunitySource(
            product_id="000123456789", location_id="01400943",
            environment="production", client_id="test-id", client_secret="test-secret",
            transport=transport,
        )
        item = source.load()[0]
        self.assertEqual(item["costo"], 9.99)
        self.assertEqual(item["location_id"], "01400943")
        self.assertEqual(item["evidence_status"], "observed")
        self.assertNotIn("Certification", " ".join(item["limitations"]))

    def test_requiere_location_y_conserva_precio_desconocido(self):
        with self.assertRaises(ValueError):
            KrogerOpportunitySource(
                product_id="1", location_id="", client_id="id", client_secret="secret"
            )
        transport = FakeTransport({"data": [{"productId": "p1", "upc": "1", "items": [{}]}]})
        item = KrogerOpportunitySource(
            product_id="1", location_id="loc", client_id="id", client_secret="secret",
            transport=transport,
        ).load()[0]
        self.assertIsNone(item["costo"])
        self.assertEqual(item["evidence_status"], "unknown")


class ProductionPilotTests(unittest.TestCase):
    def setUp(self):
        self.fees = EbayFeeAssumptions(.136, fixed=.40, shipping=5, packaging=.50)
        self.gtins = [f"0000000000{index:02d}" for index in range(10)]

    def test_readiness_no_expone_secretos(self):
        status = production_readiness(READY)
        self.assertTrue(status["ready"])
        self.assertNotIn("test-secret", repr(status))

    def test_bloquea_sin_configuracion_production(self):
        result = run_kroger_ebay_pilot(
            self.gtins, fee_assumptions=self.fees, environ={}
        )
        self.assertEqual(result["status"], "blocked_configuration")
        self.assertEqual(result["results"], [])

    def test_lote_usa_costo_observado_pero_no_emite_buy(self):
        result = run_kroger_ebay_pilot(
            self.gtins,
            fee_assumptions=self.fees,
            environ=READY,
            kroger_source_factory=FakeKrogerSource,
            ebay_source_factory=FakeEbaySource,
        )
        self.assertEqual(result["count"], 10)
        self.assertTrue(all(item["recommendation"] == "INSUFFICIENT_DATA" for item in result["results"]))
        first = result["results"][0]["analysis"]
        self.assertEqual(first["supplier_product"]["source"], "kroger_products_public")
        self.assertEqual(first["supplier_product"]["evidence_status"], "observed")
        self.assertIn("Costo observado", first["pipeline_evidence"]["cost_interpretation"])

    def test_entorno_por_defecto_y_snapshot_reproducible_no_guardan_secretos(self):
        with TemporaryDirectory() as directory, patch.dict("os.environ", READY, clear=True):
            result = run_kroger_ebay_pilot(
                self.gtins,
                fee_assumptions=self.fees,
                kroger_source_factory=FakeKrogerSource,
                ebay_source_factory=FakeEbaySource,
                snapshot_directory=directory,
            )
            snapshot = result["snapshot"]
            path = Path(snapshot["path"])
            self.assertTrue(path.is_file())
            contents = path.read_text(encoding="utf-8")
            self.assertNotIn("test-secret", contents)
            self.assertIn('"engine_version": "kroger-ebay-pilot/v1"', contents)
            self.assertEqual(len(snapshot["sha256"]), 64)

    def test_rechaza_lote_fuera_de_rango_o_gtin_duplicado(self):
        with self.assertRaises(ValueError):
            run_kroger_ebay_pilot(
                self.gtins[:9], fee_assumptions=self.fees, environ=READY
            )
        with self.assertRaises(ValueError):
            run_kroger_ebay_pilot(
                [self.gtins[0]] * 10, fee_assumptions=self.fees, environ=READY
            )


if __name__ == "__main__":
    unittest.main()
