import copy
import unittest
from datetime import datetime, timezone

from application.adapters import (
    construir_oportunidad_desde_formato_actual,
    convertir_oportunidad_a_formato_actual,
)
from application.analysis_service import analizar
from application.dashboard_service import crear_dashboard
from application.decision_service import generar_decision
from application.insight_service import generar_insights
from application.opportunity_service import puntuar_producto
from domain.entities import Opportunity, Product, Result
from domain.enums import ConfidenceLevel, EvidenceType
from domain.exceptions import DomainValidationError


def resultado_actual():
    return {
        "nombre": "Organizador",
        "precio": 29.99,
        "costo_producto": 8,
        "envio": 3.0,
        "tarifa_amazon": 4.5,
        "otros_costos": 1.0,
        "costo_total": 16.5,
        "ganancia": 13.49,
        "margen": 45.0,
        "roi": 168.6,
        "evaluacion": "EXCELENTE PRODUCTO",
        "opportunity_score": 74.2,
        "opportunity_category": "Muy prometedora",
        "opportunity_factors": {
            "roi": {
                "valor": 168.6,
                "puntos": 33.7,
                "maximo": 40.0,
                "referencia": 200.0,
            },
            "margen": {
                "valor": 45.0,
                "puntos": 27.0,
                "maximo": 30.0,
                "referencia": 50.0,
            },
            "ganancia": {
                "valor": 13.49,
                "puntos": 13.5,
                "maximo": 30.0,
                "referencia": 30.0,
            },
        },
    }


class OpportunityDomainAdapterTests(unittest.TestCase):
    def setUp(self):
        self.timestamp = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
        self.legacy = resultado_actual()
        self.opportunity = construir_oportunidad_desde_formato_actual(
            self.legacy,
            evaluated_at=self.timestamp,
        )

    def test_construye_product_oficial(self):
        self.assertIsInstance(self.opportunity.product, Product)
        self.assertEqual(self.opportunity.product.name, "Organizador")
        self.assertTrue(self.opportunity.product.product_id)

    def test_construye_opportunity_con_marketplace_opcional(self):
        self.assertIsInstance(self.opportunity, Opportunity)
        self.assertIsNone(self.opportunity.marketplace_id)
        self.assertEqual(self.opportunity.evaluated_at, self.timestamp)

    def test_cada_valor_actual_se_conserva_en_un_result(self):
        by_name = {
            result.name: result.value
            for result in self.opportunity.financial_context
        }

        for field, value in self.legacy.items():
            if field != "nombre":
                with self.subTest(field=field):
                    self.assertIn(field, by_name)
                    converted = convertir_oportunidad_a_formato_actual(
                        self.opportunity
                    )
                    self.assertEqual(converted[field], value)

    def test_results_conservan_evidencia_fuente_fecha_confianza_y_version(self):
        for result in self.opportunity.financial_context:
            with self.subTest(result=result.name):
                self.assertIsInstance(result, Result)
                self.assertEqual(result.evidence_type, EvidenceType.ESTIMATE)
                self.assertIn(result.source, {"Financial Engine", "Opportunity Engine"})
                self.assertEqual(result.recorded_at, self.timestamp)
                self.assertEqual(result.confidence, ConfidenceLevel.MEDIUM)
                self.assertEqual(result.version, "1")
                serialized = result.to_dict()
                self.assertEqual(serialized["source"], result.source)
                self.assertEqual(serialized["recorded_at"], self.timestamp.isoformat())
                self.assertEqual(serialized["confidence"], "medio")
                self.assertEqual(serialized["version"], "1")

    def test_conversion_ida_y_vuelta_no_altera_informacion(self):
        original = copy.deepcopy(self.legacy)

        converted = convertir_oportunidad_a_formato_actual(self.opportunity)

        self.assertEqual(converted, original)
        self.assertEqual(self.legacy, original)

    def test_marketplace_se_conserva_cuando_existe(self):
        legacy = resultado_actual() | {"marketplace_id": "amazon-us"}

        opportunity = construir_oportunidad_desde_formato_actual(
            legacy,
            evaluated_at=self.timestamp,
        )

        self.assertEqual(opportunity.marketplace_id, "amazon-us")
        self.assertEqual(
            convertir_oportunidad_a_formato_actual(opportunity),
            legacy,
        )

    def test_identidad_es_estable_y_no_depende_de_metricas_derivadas(self):
        repeated = construir_oportunidad_desde_formato_actual(
            copy.deepcopy(self.legacy),
            evaluated_at=self.timestamp,
        )
        without_score = {
            key: value
            for key, value in self.legacy.items()
            if not key.startswith("opportunity_")
        }
        before_enrichment = construir_oportunidad_desde_formato_actual(
            without_score,
            evaluated_at=self.timestamp,
        )

        self.assertEqual(repeated.product.product_id, self.opportunity.product.product_id)
        self.assertEqual(repeated.opportunity_id, self.opportunity.opportunity_id)
        self.assertEqual(before_enrichment.opportunity_id, self.opportunity.opportunity_id)

    def test_contextos_comerciales_distintos_generan_oportunidades_distintas(self):
        different_purchase = resultado_actual() | {"costo_producto": 9}
        different_marketplace = resultado_actual() | {"marketplace_id": "otro"}

        purchase_opportunity = construir_oportunidad_desde_formato_actual(
            different_purchase,
            evaluated_at=self.timestamp,
        )
        marketplace_opportunity = construir_oportunidad_desde_formato_actual(
            different_marketplace,
            evaluated_at=self.timestamp,
        )

        self.assertNotEqual(
            purchase_opportunity.opportunity_id,
            self.opportunity.opportunity_id,
        )
        self.assertNotEqual(
            marketplace_opportunity.opportunity_id,
            self.opportunity.opportunity_id,
        )

    def test_rechaza_entradas_invalidas(self):
        for invalid in (None, [], "producto"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(DomainValidationError):
                    construir_oportunidad_desde_formato_actual(invalid)
        with self.assertRaises(DomainValidationError):
            construir_oportunidad_desde_formato_actual({"roi": 100})


class OpportunityDomainCompatibilityTests(unittest.TestCase):
    def test_formato_antiguo_y_opportunity_score_permanecen_iguales(self):
        entrada = {
            key: value
            for key, value in resultado_actual().items()
            if not key.startswith("opportunity_")
        }

        respuesta = puntuar_producto(entrada)

        self.assertTrue(respuesta["exito"])
        self.assertEqual(respuesta["datos"], resultado_actual())
        self.assertEqual(respuesta["datos"]["opportunity_score"], 74.2)

    def test_dashboard_insights_y_decision_engine_siguen_compatibles(self):
        analysis = analizar(
            [
                {"nombre": "A", "costo": 8, "precio": 29.99},
                {"nombre": "B", "costo": 18, "precio": 44.99},
            ]
        )
        data = analysis["datos"]
        dashboard = crear_dashboard(data["resultados"], data["total_analizado"])
        insights = generar_insights(
            data["resultados_completos"],
            data["resultados"],
            dashboard["datos"],
            data["filtros_aplicados"],
        )
        decision = generar_decision(
            data["resultados_completos"],
            data["resultados"],
            dashboard["datos"],
            insights["datos"],
            data["filtros_aplicados"],
        )

        self.assertTrue(analysis["exito"])
        self.assertTrue(dashboard["exito"])
        self.assertTrue(insights["exito"])
        self.assertTrue(decision["exito"])
        self.assertIn("opportunity_score", data["resultados"][0])


if __name__ == "__main__":
    unittest.main()
