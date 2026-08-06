import unittest
from datetime import datetime, timezone

from domain.contracts import AnalysisResult, DecisionRecommendation, OpportunityResult
from domain.entities import Opportunity, Product, Recommendation, Result
from domain.enums import ConfidenceLevel, DecisionState, EvidenceType
from domain.exceptions import DomainValidationError


def opportunity():
    return Opportunity("op-1", Product("p-1", "Producto"))


def result():
    return Result(
        "result-1",
        "ROI",
        120,
        EvidenceType.ESTIMATE,
        "Financial Engine",
        recorded_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )


def recommendation():
    return Recommendation(
        "rec-1",
        DecisionState.INVESTIGATE,
        "Investiga.",
        "Faltan señales comerciales.",
        ConfidenceLevel.LOW,
        evidence=(result(),),
    )


class OpportunityResultTests(unittest.TestCase):
    def test_crea_contrato_valido(self):
        contract = OpportunityResult(opportunity(), (result(),))

        self.assertEqual(contract.opportunity.opportunity_id, "op-1")

    def test_requiere_al_menos_un_resultado(self):
        with self.assertRaises(DomainValidationError):
            OpportunityResult(opportunity(), ())

    def test_rechaza_resultados_de_tipo_incorrecto(self):
        with self.assertRaises(DomainValidationError):
            OpportunityResult(opportunity(), (object(),))


class DecisionRecommendationTests(unittest.TestCase):
    def test_crea_y_normaliza_colecciones_inmutables(self):
        missing_data = ["demanda"]
        conditions = ["confirmar marketplace"]
        contract = DecisionRecommendation(
            recommendation(),
            missing_data,
            conditions,
        )

        missing_data.clear()
        conditions.clear()
        self.assertEqual(contract.missing_data, ("demanda",))
        self.assertEqual(contract.conditions_to_advance, ("confirmar marketplace",))

    def test_rechaza_recomendacion_invalida(self):
        with self.assertRaises(DomainValidationError):
            DecisionRecommendation(object())


class AnalysisResultTests(unittest.TestCase):
    def test_permite_analisis_vacio_con_id_valido(self):
        analysis = AnalysisResult("analysis-1")

        self.assertEqual(analysis.opportunities, ())

    def test_agrega_y_serializa_contratos(self):
        opportunity_contract = OpportunityResult(opportunity(), (result(),))
        recommendation_contract = DecisionRecommendation(
            recommendation(),
            ("demanda",),
            ("investigar",),
        )
        analysis = AnalysisResult(
            "analysis-1",
            (opportunity_contract,),
            (recommendation_contract,),
            ("Estimaciones financieras.",),
        )

        serialized = analysis.to_dict()
        self.assertEqual(serialized["analysis_id"], "analysis-1")
        self.assertEqual(len(serialized["opportunities"]), 1)
        self.assertEqual(len(serialized["recommendations"]), 1)
        serialized["warnings"].append("Cambio externo")
        self.assertEqual(analysis.warnings, ("Estimaciones financieras.",))

    def test_rechaza_colecciones_incompletas(self):
        with self.assertRaises(DomainValidationError):
            AnalysisResult("analysis-1", opportunities=(object(),))


if __name__ == "__main__":
    unittest.main()
