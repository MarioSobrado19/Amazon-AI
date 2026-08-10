import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from application.goal_to_business_service import generar_caminos_candidatos
from domain.contracts import GoalToBusinessRequest, MarketplaceCatalogResult
from domain.entities import (
    BusinessModel, Marketplace, MarketplaceConditionSnapshot, Objective,
    Opportunity, OpportunityScenario, Product, Result,
)
from domain.enums import (
    CandidatePathState, ConfidenceLevel, EvidenceType, FreshnessStatus,
    InformationSource, RiskLevel, VerificationStatus,
)
from domain.value_objects import (
    ConstraintDeclaration, FrozenMapping, GoalContextSnapshot, Money,
    PreferenceDeclaration, Region,
)


NOW = datetime(2026, 8, 10, tzinfo=timezone.utc)
MARKET_ID = "11111111-1111-4111-8111-111111111111"
MODEL_ID = "22222222-2222-4222-8222-222222222222"
MODEL2_ID = "33333333-3333-4333-8333-333333333333"
SCENARIO_ID = "44444444-4444-4444-8444-444444444444"
SNAPSHOT_ID = "55555555-5555-4555-8555-555555555555"


def request(**context_values):
    context = GoalContextSnapshot("goal-1", NOW, "1", **context_values)
    return GoalToBusinessRequest(Objective("goal-1", "Crear ingreso adicional"), context, "1")


def marketplace():
    return Marketplace(MARKET_ID, "Mercado de ejemplo", Region("US"), "USD", "fuente", NOW, "1", confidence=ConfidenceLevel.HIGH)


def model(identifier=MODEL_ID, restrictions=()):
    return BusinessModel(identifier, "Modelo genérico", Region("US"), ConfidenceLevel.HIGH, "1", marketplace_id=MARKET_ID, restrictions=restrictions, source="fuente" if restrictions else None, valid_from=NOW if restrictions else None)


def opportunity():
    evidence = Result("r-1", "estimación financiera", 10, EvidenceType.ESTIMATE, "motor", ConfidenceLevel.MEDIUM, NOW, "1")
    return Opportunity("opp-1", Product("p-1", "Producto conocido"), MARKET_ID, financial_context=(evidence,), evaluated_at=NOW)


def catalog(*models, freshness=FreshnessStatus.CURRENT):
    market = marketplace()
    snapshot = MarketplaceConditionSnapshot(SNAPSHOT_ID, market, Region("US"), "condiciones", FrozenMapping(), "fuente", NOW, NOW, freshness, ConfidenceLevel.HIGH, VerificationStatus.VERIFIED, "1")
    return MarketplaceCatalogResult("catalog-1", "1", NOW, (market,), tuple(models), (snapshot,), capabilities=("logística",), confidence=ConfidenceLevel.HIGH)


class GoalToBusinessServiceTests(unittest.TestCase):
    def test_contexto_vacio_genera_camino_incompleto_y_confianza_baja(self):
        result = generar_caminos_candidatos(request())
        path = result.candidate_paths[0]
        self.assertEqual(path.state, CandidatePathState.INCOMPLETE)
        self.assertEqual(path.confidence, ConfidenceLevel.LOW)
        self.assertTrue(result.continuation_questions)

    def test_presupuesto_cero_no_se_trata_como_ausente(self):
        result = generar_caminos_candidatos(request(available_budget=Money(0, "USD")))
        capital = next(x for x in result.candidate_paths[0].assessment.dimensions if x.dimension == "capital")
        self.assertEqual(capital.evaluation, "declarada")

    def test_sin_candidatos_no_inventa_oportunidad(self):
        result = generar_caminos_candidatos(request(currency="USD"))
        path = result.candidate_paths[0]
        self.assertIsNone(path.scenario)
        self.assertIn("opportunity", path.missing_evidence)
        self.assertIn("no se inventó", result.warnings[0])

    def test_marketplace_sin_oportunidad_produce_estructura_parcial(self):
        result = generar_caminos_candidatos(request(region=Region("US")), marketplace_catalog=catalog())
        self.assertEqual(result.candidate_paths[0].state, CandidatePathState.INCOMPLETE)
        self.assertIsNotNone(result.candidate_paths[0].marketplace)

    def test_modelo_sin_oportunidad_produce_estructura_parcial(self):
        result = generar_caminos_candidatos(request(region=Region("US")), marketplace_catalog=catalog(model()))
        self.assertIsNotNone(result.candidate_paths[0].business_model)
        self.assertIn("opportunity", result.candidate_paths[0].missing_evidence)

    def test_oportunidad_marketplace_y_modelo_crean_ruta_investigable(self):
        result = generar_caminos_candidatos(request(region=Region("US")), marketplace_catalog=catalog(model()), opportunities=(opportunity(),))
        path = result.candidate_paths[0]
        self.assertEqual(path.state, CandidatePathState.RESEARCHABLE)
        self.assertIn("demanda", " ".join(path.risks).lower())
        self.assertNotIn("invertir", " ".join(path.next_steps).lower())

    def test_oportunidad_sin_estructura_operativa_es_hipotesis(self):
        path = generar_caminos_candidatos(
            request(), opportunities=(opportunity(),)
        ).candidate_paths[0]

        self.assertEqual(path.state, CandidatePathState.HYPOTHESIS)
        self.assertEqual(path.confidence, ConfidenceLevel.LOW)
        self.assertIsNone(path.marketplace)
        self.assertIsNone(path.business_model)

    def test_restriccion_dura_incompatible_invalida_y_conserva_causa(self):
        constraint = ConstraintDeclaration("sin_inventario", "No almacenar inventario", NOW, severity=RiskLevel.HIGH)
        result = generar_caminos_candidatos(request(region=Region("US"), constraints=(constraint,)), marketplace_catalog=catalog(model(restrictions=("sin_inventario",))), opportunities=(opportunity(),))
        self.assertFalse(result.candidate_paths)
        self.assertEqual(result.invalidated_paths[0].state, CandidatePathState.INVALIDATED)
        self.assertIn("No almacenar inventario", result.invalidated_paths[0].risks)
        self.assertIn("No almacenar inventario", result.invalidated_paths[0].invalidators)

    def test_preferencia_no_invalida(self):
        preference = PreferenceDeclaration("control", "alto", "Prefiero control")
        result = generar_caminos_candidatos(request(region=Region("US"), preferences=(preference,)), marketplace_catalog=catalog(model()), opportunities=(opportunity(),))
        self.assertEqual(result.candidate_paths[0].state, CandidatePathState.RESEARCHABLE)
        self.assertIn("Prefiero control", result.candidate_paths[0].related_preferences)

    def test_evidencia_expirada_se_conserva_y_reduce_confianza(self):
        result = generar_caminos_candidatos(request(region=Region("US")), marketplace_catalog=catalog(model(), freshness=FreshnessStatus.EXPIRED), opportunities=(opportunity(),))
        path = result.candidate_paths[0]
        self.assertEqual(path.confidence, ConfidenceLevel.LOW)
        self.assertIn("actualizar_condiciones", path.missing_evidence)
        self.assertTrue(any("histórica" in warning for warning in result.warnings))

    def test_multiples_modelos_generan_multiples_caminos_sin_ganador(self):
        result = generar_caminos_candidatos(request(region=Region("US")), marketplace_catalog=catalog(model(), model(MODEL2_ID)), opportunities=(opportunity(),))
        self.assertEqual(len(result.candidate_paths), 2)
        self.assertFalse(hasattr(result, "winner"))
        self.assertFalse(hasattr(result, "ranking"))

    def test_evidencia_faltante_es_explicita(self):
        path = generar_caminos_candidatos(request()).candidate_paths[0]
        self.assertTrue(path.missing_evidence)
        self.assertTrue(any(x.missing_data for x in path.assessment.dimensions))

    def test_supuestos_del_escenario_permanecen_explicitos(self):
        assumption = Result("a-1", "volumen supuesto", 5, EvidenceType.ASSUMPTION, "usuario", recorded_at=NOW)
        scenario = OpportunityScenario(SCENARIO_ID, opportunity(), marketplace(), model(), Region("US"), NOW, assumptions=(assumption,))
        path = generar_caminos_candidatos(request(region=Region("US")), scenarios=(scenario,)).candidate_paths[0]
        self.assertEqual(path.assumptions[0].evidence_type, EvidenceType.ASSUMPTION)

    def test_misma_entrada_produce_resultado_semantico_identico(self):
        kwargs = {"marketplace_catalog": catalog(model()), "opportunities": (opportunity(),)}
        first = generar_caminos_candidatos(request(region=Region("US")), **kwargs)
        second = generar_caminos_candidatos(request(region=Region("US")), **kwargs)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.candidate_paths[0].candidate_path_id, second.candidate_paths[0].candidate_path_id)

    def test_misma_hipotesis_en_timestamps_distintos_conserva_id_semantico(self):
        first_request = request(region=Region("US"))
        later_context = GoalContextSnapshot(
            "goal-1", NOW + timedelta(days=1), "1", region=Region("US")
        )
        later_request = GoalToBusinessRequest(
            Objective("goal-1", "Crear ingreso adicional"), later_context, "1"
        )
        kwargs = {"marketplace_catalog": catalog(model()), "opportunities": (opportunity(),)}
        first = generar_caminos_candidatos(first_request, generated_at=NOW, **kwargs)
        later = generar_caminos_candidatos(
            later_request, generated_at=NOW + timedelta(days=2), **kwargs
        )

        self.assertEqual(
            first.candidate_paths[0].candidate_path_id,
            later.candidate_paths[0].candidate_path_id,
        )
        self.assertNotEqual(first.generated_at, later.generated_at)

    def test_candidatos_semanticamente_duplicados_se_eliminan(self):
        known = opportunity()
        result = generar_caminos_candidatos(
            request(region=Region("US")),
            marketplace_catalog=catalog(model()),
            opportunities=(known, known),
        )
        self.assertEqual(len(result.candidate_paths), 1)

    def test_evidencia_vigente_y_expirada_coexisten(self):
        market = marketplace()
        current = MarketplaceConditionSnapshot(
            SNAPSHOT_ID, market, Region("US"), "tarifa", FrozenMapping(),
            "fuente", NOW, NOW, FreshnessStatus.CURRENT, ConfidenceLevel.HIGH,
            VerificationStatus.VERIFIED, "1",
        )
        expired = MarketplaceConditionSnapshot(
            "66666666-6666-4666-8666-666666666666", market, Region("US"),
            "política", FrozenMapping(), "fuente", NOW, NOW,
            FreshnessStatus.EXPIRED, ConfidenceLevel.MEDIUM,
            VerificationStatus.VERIFIED, "1",
        )
        mixed = MarketplaceCatalogResult(
            "catalog-mixed", "1", NOW, (market,), (model(),),
            (current, expired), confidence=ConfidenceLevel.MEDIUM,
        )
        path = generar_caminos_candidatos(
            request(region=Region("US")), marketplace_catalog=mixed,
            opportunities=(opportunity(),),
        ).candidate_paths[0]

        self.assertEqual(len(path.condition_snapshots), 2)
        self.assertEqual(
            {item.freshness for item in path.condition_snapshots},
            {FreshnessStatus.CURRENT, FreshnessStatus.EXPIRED},
        )
        self.assertEqual(path.confidence, ConfidenceLevel.LOW)

    def test_missing_data_y_confianza_baja_no_invalidan(self):
        path = generar_caminos_candidatos(request()).candidate_paths[0]
        self.assertEqual(path.state, CandidatePathState.INCOMPLETE)
        self.assertEqual(path.confidence, ConfidenceLevel.LOW)
        self.assertNotEqual(path.state, CandidatePathState.INVALIDATED)

    def test_salida_es_serializable(self):
        result = generar_caminos_candidatos(request())
        self.assertIsInstance(json.dumps(result.to_dict()), str)

    def test_serializacion_completa_de_path_assessment(self):
        assessment = generar_caminos_candidatos(request()).candidate_paths[0].assessment
        payload = assessment.to_dict()
        self.assertEqual(len(payload["dimensions"]), 11)
        for dimension in payload["dimensions"]:
            self.assertIn("explanation", dimension)
            self.assertIn("evidence", dimension)
            self.assertIn("missing_data", dimension)
            self.assertIn("relevant_constraints", dimension)
            self.assertIn("confidence", dimension)

    def test_contratos_son_inmutables_y_serializacion_no_filtra_colecciones(self):
        result = generar_caminos_candidatos(request())
        with self.assertRaises(FrozenInstanceError):
            result.version = "2"
        serialized = result.to_dict()
        serialized["candidate_paths"].clear()
        self.assertEqual(len(result.candidate_paths), 1)

    def test_no_existe_score_global_probabilidad_o_promesa(self):
        result = generar_caminos_candidatos(request())
        payload = json.dumps(result.to_dict(), ensure_ascii=False).lower()
        self.assertNotIn('"score"', payload)
        self.assertNotIn("probabilidad de éxito", payload)
        self.assertNotIn("ganancia garantizada", payload)
        for forbidden in ("listo para invertir", "debes invertir", "debes comprar", "listo para probar"):
            self.assertNotIn(forbidden, payload)

    def test_no_inventa_productos_marketplaces_o_proveedores(self):
        path = generar_caminos_candidatos(request()).candidate_paths[0]
        self.assertIsNone(path.marketplace)
        self.assertIsNone(path.business_model)
        self.assertIsNone(path.scenario)

    def test_region_incompatible_invalida(self):
        result = generar_caminos_candidatos(request(region=Region("CA")), marketplace_catalog=catalog(model()), opportunities=(opportunity(),))
        self.assertEqual(result.invalidated_paths[0].state, CandidatePathState.INVALIDATED)

    def test_dimensiones_requeridas_estan_presentes_y_sin_score(self):
        assessment = generar_caminos_candidatos(request()).candidate_paths[0].assessment
        self.assertEqual(len(assessment.dimensions), 11)
        self.assertFalse(hasattr(assessment, "score"))

    def test_rechaza_entrada_no_contractual(self):
        with self.assertRaises(Exception):
            generar_caminos_candidatos(object())


if __name__ == "__main__":
    unittest.main()
