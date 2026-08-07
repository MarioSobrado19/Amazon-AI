import copy
import unittest
from datetime import datetime, timezone

from application.adapters.decision_domain_adapter import (
    construir_analisis_decision,
    construir_recomendacion_dominio,
    convertir_recomendacion_a_formato_actual,
    convertir_resultados_a_formato_actual,
)
from application.dashboard_service import crear_dashboard
from application.decision_service import (
    _generar_decision_heredada,
    generar_decision,
    generar_decision_dominio,
)
from domain.contracts import AnalysisResult, DecisionRecommendation
from domain.entities import Opportunity, Recommendation, Result
from domain.enums import DecisionState, EvidenceType
from domain.exceptions import DomainValidationError


def producto(nombre="Líder", score=82, **overrides):
    item = {
        "nombre": nombre,
        "costo_producto": 8.0,
        "precio": 29.99,
        "costo_total": 16.5,
        "ganancia": 13.49,
        "margen": 45.0,
        "roi": 168.6,
        "evaluacion": "EXCELENTE PRODUCTO",
        "opportunity_score": score,
        "opportunity_category": "Muy prometedora",
        "opportunity_factors": {"roi": 35.0, "margen": 25.0, "ganancia": 22.0},
    }
    item.update(overrides)
    return item


def dashboard(items, total=None):
    respuesta = crear_dashboard(items, len(items) if total is None else total)
    if not respuesta["exito"]:
        raise AssertionError(respuesta["errores"])
    return respuesta["datos"]


def insights():
    return {
        "riesgos_detectados": ["Riesgo observado."],
    }


def decision_legacy(completos, filtrados=None, contexto=None):
    filtrados = completos if filtrados is None else filtrados
    return _generar_decision_heredada(
        completos,
        filtrados,
        dashboard(filtrados, len(completos)),
        insights(),
        {},
        contexto,
    )


class DecisionDomainAdapterTests(unittest.TestCase):
    def test_construye_analysis_opportunity_y_results_oficiales(self):
        analysis = construir_analisis_decision([producto()])

        self.assertIsInstance(analysis, AnalysisResult)
        self.assertIsInstance(analysis.opportunities[0].opportunity, Opportunity)
        self.assertTrue(
            all(isinstance(item, Result) for item in analysis.opportunities[0].results)
        )

    def test_results_conservan_valores_y_metadatos(self):
        analysis = construir_analisis_decision([producto()])
        result = next(
            item for item in analysis.opportunities[0].results
            if item.name == "opportunity_score"
        )

        self.assertEqual(result.value, 82)
        self.assertEqual(result.evidence_type, EvidenceType.ESTIMATE)
        self.assertEqual(result.source, "Opportunity Engine")
        self.assertIsNotNone(result.recorded_at.tzinfo)
        self.assertEqual(result.confidence.value, "medio")
        self.assertEqual(result.version, "1")

    def test_round_trip_de_resultados_anidados_es_exacto(self):
        original = [producto(metadata={"tags": ["hogar", "piloto"]})]
        analysis = construir_analisis_decision(original)

        self.assertEqual(
            convertir_resultados_a_formato_actual(analysis.opportunities),
            original,
        )

    def test_construye_recommendation_trazable_y_completa(self):
        current = [producto()]
        analysis = construir_analisis_decision(current)
        legacy = decision_legacy(current)["datos"]
        contract = construir_recomendacion_dominio(
            legacy,
            analysis.opportunities,
            primary_opportunity_id=analysis.opportunities[0].opportunity.opportunity_id,
            created_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        )
        recommendation = contract.recommendation

        self.assertIsInstance(contract, DecisionRecommendation)
        self.assertIsInstance(recommendation, Recommendation)
        self.assertEqual(recommendation.state, DecisionState.INVESTIGATE)
        self.assertEqual(
            recommendation.opportunity_id,
            analysis.opportunities[0].opportunity.opportunity_id,
        )
        self.assertEqual(recommendation.evidence, analysis.opportunities[0].results)
        self.assertEqual(recommendation.version, "1")
        self.assertIsNotNone(recommendation.created_at.tzinfo)
        self.assertEqual(dict(recommendation.context_used), legacy["contexto_utilizado"])

    def test_round_trip_recommendation_conserva_salida_heredada_exacta(self):
        current = [producto()]
        legacy = decision_legacy(current)["datos"]
        analysis = construir_analisis_decision(current)
        contract = construir_recomendacion_dominio(legacy, analysis.opportunities)

        self.assertEqual(convertir_recomendacion_a_formato_actual(contract), legacy)

    def test_adaptadores_rechazan_entradas_invalidas(self):
        with self.assertRaises(DomainValidationError):
            construir_analisis_decision(None)
        with self.assertRaises(DomainValidationError):
            convertir_resultados_a_formato_actual((object(),))
        with self.assertRaises(DomainValidationError):
            construir_recomendacion_dominio({})
        with self.assertRaises(DomainValidationError):
            convertir_recomendacion_a_formato_actual(object())


class DecisionDomainCompatibilityTests(unittest.TestCase):
    def test_engine_consume_analysis_result_y_devuelve_contrato(self):
        current = [producto()]
        analysis = construir_analisis_decision(current)
        response = generar_decision_dominio(
            analysis,
            analysis,
            dashboard(current),
            insights(),
            {},
        )

        self.assertTrue(response["exito"])
        self.assertIsInstance(response["datos"], DecisionRecommendation)
        self.assertEqual(
            response["datos"].recommendation.opportunity_id,
            analysis.opportunities[0].opportunity.opportunity_id,
        )

    def test_recommendation_traza_resultados_completos_y_filtrados(self):
        complete_items = [producto("Líder", 82), producto("Descartado", 20)]
        filtered_items = complete_items[:1]
        complete = construir_analisis_decision(complete_items, "complete")
        filtered = construir_analisis_decision(filtered_items, "filtered")
        response = generar_decision_dominio(
            complete,
            filtered,
            dashboard(filtered_items, len(complete_items)),
            insights(),
            {"roi_minimo": 100},
        )
        evidence_ids = {
            item.result_id for item in response["datos"].recommendation.evidence
        }

        for opportunity_result in complete.opportunities:
            self.assertTrue(
                {item.result_id for item in opportunity_result.results}.issubset(evidence_ids)
            )

    def test_misma_entrada_conserva_exactamente_recomendacion_actual(self):
        current = [producto()]
        expected = decision_legacy(current)
        actual = generar_decision(
            current,
            current,
            dashboard(current),
            insights(),
            {},
        )

        self.assertEqual(actual, expected)

    def test_score_favorable_con_o_sin_presupuesto_sigue_investigar(self):
        for context in (None, {"presupuesto": 75}):
            with self.subTest(context=context):
                response = generar_decision(
                    [producto()], [producto()], dashboard([producto()]), insights(), {}, context
                )
                self.assertEqual(response["datos"]["estado"], "investigar")

    def test_estado_probar_nunca_se_genera(self):
        scenarios = (
            ([], []),
            ([producto(score=20, evaluacion="NO RECOMENDADO")], None),
            ([producto()], None),
            ([producto("A", 82), producto("B", 79)], None),
        )
        for complete, filtered in scenarios:
            filtered = complete if filtered is None else filtered
            response = generar_decision(
                complete,
                filtered,
                dashboard(filtered, len(complete)),
                insights(),
                {},
            )
            self.assertNotEqual(response["datos"]["estado"], "probar")

    def test_similares_debiles_vacios_y_principiante_conservan_reglas(self):
        cases = (
            ([producto("A", 82), producto("B", 79)], None, "comparar"),
            ([producto(score=20, evaluacion="NO RECOMENDADO")], None, "posponer"),
            ([], None, "explorar"),
            ([producto()], {"experiencia": "principiante"}, "investigar"),
        )
        for items, context, expected in cases:
            response = generar_decision(
                items, items, dashboard(items), insights(), {}, context
            )
            self.assertEqual(response["datos"]["estado"], expected)
            if context:
                self.assertTrue(response["datos"]["proximo_paso"].startswith("Primer paso:"))

    def test_confianza_y_textos_se_conservan_sin_promesas(self):
        response = generar_decision(
            [producto()], [producto()], dashboard([producto()]), insights(), {}
        )
        data = response["datos"]
        text = " ".join(
            [data["recomendacion_principal"], data["resumen"], data["proximo_paso"], *data["limitaciones"]]
        ).casefold()

        self.assertEqual(data["nivel_confianza"], "bajo")
        for forbidden in ("compra ahora", "invierte ahora", "debes comprar", "rentabilidad garantizada"):
            self.assertNotIn(forbidden, text)

    def test_no_modifica_resultados_ni_recalcula_score(self):
        current = [producto(score=74.2)]
        before = copy.deepcopy(current)
        response = generar_decision(
            current, current, dashboard(current), insights(), {}
        )

        self.assertTrue(response["exito"])
        self.assertEqual(current, before)
        self.assertEqual(current[0]["opportunity_score"], 74.2)


if __name__ == "__main__":
    unittest.main()
