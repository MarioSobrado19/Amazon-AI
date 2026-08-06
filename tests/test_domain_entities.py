import unittest
from datetime import datetime, timezone

from domain.entities import Opportunity, Product, Recommendation, Result
from domain.enums import ConfidenceLevel, DecisionState, EvidenceType, RiskLevel
from domain.exceptions import DomainValidationError
from domain.value_objects import Money, Percentage


def product(product_id="product-1", name="Organizador"):
    return Product(product_id, name)


def result(result_id="result-1"):
    return Result(
        result_id=result_id,
        name="ROI",
        value=Percentage("125.4"),
        evidence_type=EvidenceType.ESTIMATE,
        source="Financial Engine v1",
        confidence=ConfidenceLevel.MEDIUM,
        recorded_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )


class ProductTests(unittest.TestCase):
    def test_crea_producto_valido_y_normaliza_texto(self):
        item = Product(
            " p-1 ",
            " Organizador ",
            external_identifiers=(("ASIN", "B0001"),),
        )

        self.assertEqual(item.product_id, "p-1")
        self.assertEqual(item.name, "Organizador")
        self.assertEqual(item.external_identifiers, (("ASIN", "B0001"),))

    def test_nombre_es_obligatorio(self):
        with self.assertRaises(DomainValidationError):
            Product("p-1", "  ")

    def test_identidad_depende_del_product_id(self):
        self.assertEqual(Product("p-1", "A"), Product("p-1", "B"))
        self.assertNotEqual(Product("p-1", "A"), Product("p-2", "A"))

    def test_rechaza_identificadores_externos_incompletos(self):
        with self.assertRaises(DomainValidationError):
            Product("p-1", "A", external_identifiers=(("ASIN",),))

    def test_serializa_producto(self):
        item = Product(
            "p-1",
            "A",
            external_identifiers=(("ASIN", "B1"),),
        )
        serialized = item.to_dict()

        self.assertEqual(serialized["external_identifiers"], {"ASIN": "B1"})
        serialized["external_identifiers"]["ASIN"] = "CAMBIADO"
        self.assertEqual(item.external_identifiers, (("ASIN", "B1"),))


class OpportunityTests(unittest.TestCase):
    def test_crea_oportunidad_sin_marketplace_en_exploracion(self):
        opportunity = Opportunity("op-1", product())

        self.assertIsNone(opportunity.marketplace_id)

    def test_debe_referenciar_un_product(self):
        with self.assertRaises(DomainValidationError):
            Opportunity("op-1", object())

    def test_identidad_depende_del_opportunity_id(self):
        self.assertEqual(
            Opportunity("op-1", product("p-1")),
            Opportunity("op-1", product("p-2")),
        )

    def test_serializa_producto_referenciado(self):
        serialized = Opportunity("op-1", product()).to_dict()

        self.assertEqual(serialized["product"]["product_id"], "product-1")


class ResultTests(unittest.TestCase):
    def test_crea_resultado_con_naturaleza_explicita(self):
        domain_result = result()

        self.assertEqual(domain_result.evidence_type, EvidenceType.ESTIMATE)
        self.assertEqual(domain_result.confidence, ConfidenceLevel.MEDIUM)

    def test_rechaza_resultado_sin_tipo_de_evidencia(self):
        with self.assertRaises(DomainValidationError):
            Result("r-1", "ROI", 100, None, "Financial Engine")

    def test_rechaza_resultado_sin_fuente(self):
        with self.assertRaises(DomainValidationError):
            Result("r-1", "ROI", 100, EvidenceType.ESTIMATE, "")
        with self.assertRaises(DomainValidationError):
            Result(
                "r-1",
                "ROI",
                {"valor": 100},
                EvidenceType.ESTIMATE,
                "Financial Engine",
            )

    def test_rechaza_fecha_sin_zona_horaria(self):
        with self.assertRaises(DomainValidationError):
            Result(
                "r-1",
                "ROI",
                100,
                EvidenceType.ESTIMATE,
                "Financial Engine",
                recorded_at=datetime(2026, 8, 6),
            )

    def test_serializa_value_object_y_enums(self):
        serialized = result().to_dict()

        self.assertEqual(serialized["value"], {"value": "125.4"})
        self.assertEqual(serialized["evidence_type"], "estimacion")
        self.assertTrue(serialized["recorded_at"].endswith("+00:00"))


class RecommendationTests(unittest.TestCase):
    def test_crea_recomendacion_explicable(self):
        evidence = [result()]
        risks = [(RiskLevel.HIGH, "Demanda desconocida.")]
        recommendation = Recommendation(
            recommendation_id="rec-1",
            state=DecisionState.INVESTIGATE,
            message="Investiga antes de avanzar.",
            explanation="Faltan datos comerciales verificados.",
            confidence=ConfidenceLevel.LOW,
            evidence=evidence,
            risks=risks,
        )

        evidence.clear()
        risks.clear()
        self.assertEqual(recommendation.state, DecisionState.INVESTIGATE)
        self.assertEqual(len(recommendation.evidence), 1)
        self.assertEqual(len(recommendation.risks), 1)

    def test_nunca_existe_sin_explicacion(self):
        with self.assertRaises(DomainValidationError):
            Recommendation(
                "rec-1",
                DecisionState.INVESTIGATE,
                "Investiga.",
                " ",
                ConfidenceLevel.LOW,
            )

    def test_rechaza_evidencia_invalida(self):
        with self.assertRaises(DomainValidationError):
            Recommendation(
                "rec-1",
                DecisionState.INVESTIGATE,
                "Investiga.",
                "Faltan datos.",
                ConfidenceLevel.LOW,
                evidence=(object(),),
            )

    def test_serializa_sin_perder_explicacion(self):
        recommendation = Recommendation(
            "rec-1",
            DecisionState.INVESTIGATE,
            "Investiga.",
            "Faltan datos comerciales.",
            ConfidenceLevel.LOW,
            evidence=(result(),),
        )

        self.assertEqual(
            recommendation.to_dict()["explanation"],
            "Faltan datos comerciales.",
        )


class DomainEntityCompletenessTests(unittest.TestCase):
    def test_rechaza_identificadores_vacios(self):
        constructors = (
            lambda: Product("", "Producto"),
            lambda: Opportunity("", product()),
            lambda: Result("", "ROI", 1, EvidenceType.DATA, "fuente"),
            lambda: Recommendation(
                "",
                DecisionState.EXPLORE,
                "Explora.",
                "No hay resultados.",
                ConfidenceLevel.LOW,
            ),
        )

        for constructor in constructors:
            with self.subTest(constructor=constructor):
                with self.assertRaises(DomainValidationError):
                    constructor()


if __name__ == "__main__":
    unittest.main()
