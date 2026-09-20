import unittest
import subprocess
import sys

from application.ebay_production_pipeline import run_ebay_production_pipeline
from application.listing_valuation import value_listings
from application.resale_economics import EbayFeeAssumptions


class FakeEbaySource:
    environment = "production"

    def __init__(self, details):
        self.details = details if isinstance(details, list) else [details]

    def load(self):
        return [
            {
                "nombre": f"Observed listing {index}",
                "precio": 24.99 + index,
                "currency": "USD",
                "condition": "New",
                "ebay_item_id": f"v1|{index}|0",
                "source": "ebay_browse",
                "evidence_status": "observed",
                "limitations": ["Listing activo; no es una venta."],
            }
            for index in range(len(self.details))
        ]

    def get_item(self, item_id):
        self.item_id = item_id
        index = int(item_id.split("|")[1])
        return self.details[index]


class EbayProductionPipelineTests(unittest.TestCase):
    def setUp(self):
        self.fees = EbayFeeAssumptions(
            percentage=.136,
            fixed=.40,
            shipping=5.00,
            acquisition_sales_tax=0,
            packaging=.50,
            promotion_percentage=0,
            other=0,
        )

    def test_pipeline_completo_exige_gtin_observado_en_detalle(self):
        source = FakeEbaySource([
            {
                "title": "Exact product 48 ct", "condition": "New",
                "localizedAspects": [
                    {"name": "UPC", "value": "629721670295"},
                    {"name": "Brand", "value": "Great Value"},
                    {"name": "Number of Units", "value": "48"},
                ],
                "shippingOptions": [{"shippingCost": {"value": "4.00"}}],
            },
            {
                "title": "Exact product 48 ct", "condition": "New",
                "localizedAspects": [
                    {"name": "UPC", "value": "629721670295"},
                    {"name": "Brand", "value": "Great Value"},
                    {"name": "Number of Units", "value": "48"},
                ],
                "shippingOptions": [{"shippingCost": {"value": "0"}}],
            },
        ])
        result = run_ebay_production_pipeline(
            gtin="629721670295", manual_cost=8, fee_assumptions=self.fees,
            source=source,
        )

        self.assertEqual(result["status"], "financially_scored")
        self.assertEqual(result["commercial_status"], "commercially_unverified")
        self.assertEqual(len(result["listing_scenarios"]), 2)
        self.assertTrue(all(item["match"]["confidence"] == "high" for item in result["listing_scenarios"]))
        self.assertEqual(result["supplier_product"]["source"], "manual_controlled_validation")
        self.assertEqual(result["supplier_product"]["evidence_status"], "ASSUMPTION")
        self.assertEqual(result["valuation"]["confidence"], "low")
        self.assertIsNone(result["valuation"]["representative_price"])
        self.assertEqual(result["valuation"]["advertised_price"]["observable_median"], 25.49)
        self.assertEqual(result["valuation"]["delivered_price"]["observable_median"], 27.49)
        self.assertFalse(result["states"]["research_ready"])
        self.assertEqual(
            result["states"]["current"],
            ["financially_scored", "commercially_unverified"],
        )
        self.assertIn("precio representativo confiable", result["research_readiness"]["missing"])
        self.assertEqual(result["valuation"]["listings"][0]["identity_validation"]["gtin"], "exact")
        self.assertIn("no es una venta confirmada", result["pipeline_evidence"]["price_interpretation"])
        self.assertEqual(source.item_id, "v1|1|0")

    def test_rechaza_listing_si_detalle_no_confirma_gtin(self):
        source = FakeEbaySource({"gtin": "000000000000"})
        result = run_ebay_production_pipeline(
            gtin="629721670295", manual_cost=8, fee_assumptions=self.fees,
            source=source,
        )

        self.assertEqual(result["status"], "commercially_unverified")
        self.assertEqual(result["pipeline_evidence"]["listing_details_rejected"], 1)

    def test_requiere_supuestos_tipados_y_costo_valido(self):
        with self.assertRaises(TypeError):
            run_ebay_production_pipeline(
                gtin="629721670295", manual_cost=8, fee_assumptions={},
                source=FakeEbaySource({}),
            )
        with self.assertRaises(ValueError):
            run_ebay_production_pipeline(
                gtin="629721670295", manual_cost=0, fee_assumptions=self.fees,
                source=FakeEbaySource({}),
            )

    def test_submodulo_no_carga_dependencias_del_legado(self):
        code = (
            "import application.ebay_production_pipeline, sys; "
            "assert 'application.analysis_service' not in sys.modules"
        )
        completed = subprocess.run([sys.executable, "-c", code], check=False)
        self.assertEqual(completed.returncode, 0)

    def test_presentacion_incompatible_se_rechaza(self):
        result = run_ebay_production_pipeline(
            gtin="629721670295", manual_cost=8, fee_assumptions=self.fees,
            source=FakeEbaySource([
                {"gtin": "629721670295", "condition": "New", "localizedAspects": [{"name": "Brand", "value": "A"}]},
                {"gtin": "629721670295", "condition": "Used", "localizedAspects": [{"name": "Brand", "value": "A"}]},
            ]),
        )
        self.assertEqual(result["valuation"]["comparable_count"], 1)
        self.assertIn("condition", result["valuation"]["listings"][1]["presentation_validation"]["conflicts"])

    def test_mediana_representativa_requiere_minimo_y_excluye_outlier(self):
        listings = []
        for index, price in enumerate((20.0, 21.0, 22.0, 100.0)):
            listings.append({
                "ebay_item_id": str(index), "advertised_price": price,
                "delivered_price": price + 5, "presentation": {
                    "brand": "brand", "quantity": "48", "size_weight": "1 lb",
                    "variant": "medium", "condition": "new", "currency": "usd",
                },
            })
        valuation = value_listings(listings, minimum_comparables=3)
        self.assertEqual(valuation["outlier_item_ids"], ["3"])
        self.assertEqual(valuation["representative_price"], 21.0)
        self.assertEqual(valuation["advertised_price"]["observable_median"], 21.5)
        self.assertEqual(valuation["advertised_price"]["minimum"], 20.0)
        self.assertEqual(valuation["advertised_price"]["maximum"], 100.0)


if __name__ == "__main__":
    unittest.main()
