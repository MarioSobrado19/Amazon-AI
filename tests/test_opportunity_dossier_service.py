from datetime import datetime, timedelta, timezone
import json
import unittest

from application.opportunity_dossier_service import (
    DOSSIER_VERSION,
    crear_expediente_oportunidad,
    exportar_expediente_json,
    exportar_expediente_txt,
)


def pipeline_result(*, listing_id="v1|1|0", observed_at="2026-09-19T12:00:00+00:00"):
    assumptions = {
        "percentage": .136,
        "fixed": .4,
        "shipping": 5,
        "taxes": 0,
        "other": 0,
        "acquisition_sales_tax": 0,
        "packaging": .5,
        "promotion_percentage": 0,
        "percentage_fee": 3.4,
        "promotion_fee": 0,
    }
    return {
        "pipeline_evidence": {
            "gtin": "629721670295",
            "ebay_environment": "production",
            "active_listings_observed": 1,
            "exact_gtin_listings_accepted": 1,
        },
        "supplier_product": {
            "costo": 8,
            "source": "manual_controlled_validation",
        },
        "valuation": {
            "listings": [{
                "ebay_item_id": listing_id,
                "observed_at": observed_at,
                "advertised_price": 25,
            }],
            "advertised_price": {
                "minimum": 25,
                "maximum": 25,
                "observable_median": 25,
            },
            "usable_comparable_count": 1,
            "confidence": "low",
            "representative_price": None,
        },
        "listing_scenarios": [{
            "market_listing": {
                "ebay_item_id": listing_id,
                "nombre": "Producto exacto",
            },
            "economics": {
                "known": {"resale_price": 25, "cost": 8},
                "assumptions": assumptions,
                "costo_total": 17.3,
                "ganancia": 7.7,
                "margen": 30.8,
                "roi": 96.2,
            },
            "oriva": {
                "opportunity_score": 70,
                "opportunity_category": "Muy prometedora",
            },
        }],
        "research_readiness": {
            "status": "not_ready",
            "missing": [
                "ventas completadas o señal legítima de demanda",
                "proveedor y costo verificables",
                "precio representativo confiable",
            ],
        },
    }


class OpportunityDossierTests(unittest.TestCase):
    def test_separa_datos_supuestos_y_desconocidos(self):
        dossier = crear_expediente_oportunidad(
            pipeline_result(), generated_at=datetime(2026, 9, 19, tzinfo=timezone.utc)
        )

        self.assertEqual(dossier["version"], DOSSIER_VERSION)
        self.assertTrue(all(item["evidence_type"] == "DATA" for item in dossier["evidence"]["observed"]))
        self.assertTrue(all(item["evidence_type"] == "ASSUMPTION" for item in dossier["evidence"]["assumptions"]))
        self.assertIn("proveedor y costo verificables", dossier["evidence"]["unknown"])
        self.assertFalse(dossier["guidance"]["purchase_authorized"])

    def test_misma_evidencia_con_distinta_fecha_conserva_identidad(self):
        first = crear_expediente_oportunidad(
            pipeline_result(), generated_at=datetime(2026, 9, 19, tzinfo=timezone.utc)
        )
        second = crear_expediente_oportunidad(
            pipeline_result(), generated_at=datetime(2026, 9, 20, tzinfo=timezone.utc)
        )

        self.assertEqual(first["dossier_id"], second["dossier_id"])
        self.assertNotEqual(first["generated_at"], second["generated_at"])

    def test_evidencia_distinta_genera_expediente_distinto(self):
        first = crear_expediente_oportunidad(pipeline_result())
        second = crear_expediente_oportunidad(
            pipeline_result(listing_id="v1|2|0")
        )

        self.assertNotEqual(first["dossier_id"], second["dossier_id"])

    def test_orden_de_evidencia_no_cambia_identidad(self):
        first_input = pipeline_result()
        second_listing = {
            "ebay_item_id": "v1|2|0",
            "observed_at": "2026-09-19T12:00:01+00:00",
            "advertised_price": 26,
        }
        first_input["valuation"]["listings"].append(second_listing)
        second_input = pipeline_result()
        second_input["valuation"]["listings"] = [
            second_listing,
            *second_input["valuation"]["listings"],
        ]

        first = crear_expediente_oportunidad(first_input)
        second = crear_expediente_oportunidad(second_input)

        self.assertEqual(first["dossier_id"], second["dossier_id"])

    def test_conserva_timezone_no_utc(self):
        eastern = timezone(timedelta(hours=-4))
        dossier = crear_expediente_oportunidad(
            pipeline_result(), generated_at=datetime(2026, 9, 19, 8, tzinfo=eastern)
        )

        self.assertTrue(dossier["generated_at"].endswith("-04:00"))

    def test_rechaza_fecha_sin_timezone_y_resultado_incompleto(self):
        with self.assertRaisesRegex(ValueError, "zona horaria"):
            crear_expediente_oportunidad(
                pipeline_result(), generated_at=datetime(2026, 9, 19)
            )
        with self.assertRaisesRegex(ValueError, "incompleto"):
            crear_expediente_oportunidad({})

    def test_sin_escenarios_permanece_como_evidencia_insuficiente(self):
        result = pipeline_result()
        result["listing_scenarios"] = []
        dossier = crear_expediente_oportunidad(result)

        self.assertEqual(
            dossier["guidance"]["state"], "insufficient_comparable_evidence"
        )
        self.assertEqual(dossier["financial_scenarios"], ())

    def test_no_contiene_orden_de_compra_ni_promesa(self):
        dossier = crear_expediente_oportunidad(pipeline_result())
        text = json.dumps(dossier, ensure_ascii=False).casefold()

        self.assertNotIn("debes comprar", text)
        self.assertNotIn("rentabilidad garantizada", text)
        self.assertIn("no autoriza", text)

    def test_exporta_json_trazable_y_txt_legible(self):
        dossier = crear_expediente_oportunidad(
            pipeline_result(), generated_at=datetime(2026, 9, 19, tzinfo=timezone.utc)
        )
        json_export = exportar_expediente_json(dossier)
        text_export = exportar_expediente_txt(dossier)
        decoded = json.loads(json_export["contenido"])

        self.assertEqual(decoded["dossier_id"], dossier["dossier_id"])
        self.assertEqual(json_export["mime"], "application/json")
        self.assertIn("DATOS FALTANTES", text_export["contenido"].decode())
        self.assertIn("No autoriza comprar", text_export["contenido"].decode())


if __name__ == "__main__":
    unittest.main()
