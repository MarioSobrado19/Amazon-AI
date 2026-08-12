import json
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

from application.business_path_service import (
    promote_candidate_business_path,
    reevaluate_business_path,
    transition_business_path,
)
from domain.contracts import CandidateBusinessPath, PathAssessment
from domain.entities import (
    BusinessModel, Marketplace, Objective, Opportunity, OpportunityScenario,
    Product, Result,
)
from domain.enums import (
    BusinessPathState, CandidatePathState, ConfidenceLevel, EvidenceType,
    PathPromotionAction,
)
from domain.exceptions import DomainValidationError
from domain.value_objects import GoalContextSnapshot, Money, Region


NOW = datetime(2026, 8, 10, tzinfo=timezone.utc)
CANDIDATE_ID = "11111111-1111-4111-8111-111111111111"
MARKET_ID = "22222222-2222-4222-8222-222222222222"
MODEL_ID = "33333333-3333-4333-8333-333333333333"
SCENARIO_ID = "44444444-4444-4444-8444-444444444444"


def context(version="1", captured_at=NOW, **values):
    return GoalContextSnapshot(
        "goal-1", captured_at, version, region=Region("US"), **values
    )


def scenario(identifier=SCENARIO_ID, model_id=MODEL_ID):
    market = Marketplace(MARKET_ID, "Mercado", Region("US"), "USD", "fuente", NOW, "1")
    model = BusinessModel(model_id, "Modelo", Region("US"), ConfidenceLevel.MEDIUM, "1", marketplace_id=MARKET_ID)
    opportunity = Opportunity("opp-1", Product("p-1", "Producto"), MARKET_ID, evaluated_at=NOW)
    return OpportunityScenario(identifier, opportunity, market, model, Region("US"), NOW)


def candidate(identifier=CANDIDATE_ID, state=CandidatePathState.INCOMPLETE, snapshot=None, path_scenario=None, confidence=ConfidenceLevel.LOW):
    path_scenario = path_scenario
    return CandidateBusinessPath(
        candidate_path_id=identifier,
        objective_id="goal-1",
        context=snapshot or context(),
        assessment=PathAssessment((), confidence, "1"),
        state=state,
        confidence=confidence,
        version="1",
        marketplace=path_scenario.marketplace if path_scenario else None,
        business_model=path_scenario.business_model if path_scenario else None,
        scenario=path_scenario,
        missing_evidence=("demanda",),
        risks=("Falta evidencia comercial.",),
        next_steps=("Investigar demanda.",),
    )


def promote(item=None, **overrides):
    values = {
        "candidate": item or candidate(),
        "action": PathPromotionAction.SAVE,
        "actor_id": "user-1",
        "promoted_at": NOW,
    }
    values.update(overrides)
    return promote_candidate_business_path(**values)


class BusinessPathPromotionTests(unittest.TestCase):
    def test_promocion_valida_crea_ruta_guardada(self):
        result = promote()
        self.assertEqual(result.business_path.state, BusinessPathState.SAVED)
        self.assertEqual(result.business_path.source_candidate_id, CANDIDATE_ID)

    def test_promocion_requiere_accion_humana_explicita(self):
        with self.assertRaises(DomainValidationError):
            promote(action=None)
        with self.assertRaises(DomainValidationError):
            promote(actor_id=" ")

    def test_incomplete_puede_promoverse_para_investigacion(self):
        result = promote(action=PathPromotionAction.INVESTIGATE)
        self.assertEqual(result.business_path.state, BusinessPathState.INVESTIGATING)
        self.assertTrue(result.warnings)

    def test_invalidated_no_es_promocionable(self):
        with self.assertRaises(DomainValidationError):
            promote(candidate(state=CandidatePathState.INVALIDATED))

    def test_promocion_duplicada_se_rechaza(self):
        first = promote().business_path
        with self.assertRaises(DomainValidationError):
            promote(existing_paths=(first,))

    def test_misma_hipotesis_genera_misma_identidad_persistente(self):
        first = promote().business_path
        second = promote(promoted_at=NOW + timedelta(days=1)).business_path
        self.assertEqual(first.business_path_id, second.business_path_id)

    def test_candidatos_equivalentes_con_ids_distintos_no_crean_duplicado(self):
        shared = scenario()
        first = promote(candidate(CANDIDATE_ID, path_scenario=shared)).business_path
        equivalent = candidate(
            "88888888-8888-4888-8888-888888888888", path_scenario=shared
        )
        with self.assertRaises(DomainValidationError):
            promote(equivalent, existing_paths=(first,))

    def test_mismo_escenario_con_contexto_distinto_conserva_identidad(self):
        shared = scenario()
        first = promote(candidate(CANDIDATE_ID, path_scenario=shared)).business_path
        changed = context("2", NOW + timedelta(days=1))
        second = promote(
            candidate(
                "99999999-9999-4999-8999-999999999999",
                snapshot=changed,
                path_scenario=shared,
            )
        ).business_path
        self.assertEqual(first.business_path_id, second.business_path_id)
        self.assertEqual(first.scenario_ids, second.scenario_ids)

    def test_business_model_distinto_cambia_identidad(self):
        first = promote(candidate(path_scenario=scenario())).business_path
        changed_model = scenario(
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        )
        second = promote(
            candidate(
                "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                path_scenario=changed_model,
            )
        ).business_path
        self.assertNotEqual(first.business_path_id, second.business_path_id)

    def test_distintos_escenarios_generan_rutas_distintas(self):
        first_scenario = scenario()
        second_scenario = scenario("55555555-5555-4555-8555-555555555555")
        first = promote(candidate(CANDIDATE_ID, path_scenario=first_scenario)).business_path
        second = promote(candidate("66666666-6666-4666-8666-666666666666", path_scenario=second_scenario)).business_path
        self.assertNotEqual(first.business_path_id, second.business_path_id)
        self.assertNotEqual(first.scenario_ids, second.scenario_ids)

    def test_contextos_distintos_permanecen_independientes(self):
        first = promote().business_path
        second_context = context("2", NOW + timedelta(days=1))
        second = promote(candidate("77777777-7777-4777-8777-777777777777", snapshot=second_context)).business_path
        self.assertEqual(first.business_path_id, second.business_path_id)
        self.assertNotEqual(first.context, second.context)
        self.assertEqual(first.context.version, "1")

    def test_referencia_escenario_sin_duplicarlo_en_serializacion(self):
        path = promote(candidate(path_scenario=scenario())).business_path
        payload = path.to_dict()
        self.assertEqual(payload["scenario_ids"], [SCENARIO_ID])
        self.assertNotIn("scenarios", payload)

    def test_resultado_de_promocion_es_trazable(self):
        result = promote(reason="El usuario decidió conservarlo.")
        self.assertEqual(result.actor_id, "user-1")
        self.assertEqual(result.business_path.state_change_reason, "El usuario decidió conservarlo.")
        self.assertEqual(result.source_candidate.candidate_path_id, CANDIDATE_ID)


class BusinessPathTransitionTests(unittest.TestCase):
    def transition(self, path, state, **overrides):
        values = {"actor_id": "user-1", "reason": "Cambio explícito", "evaluated_at": NOW + timedelta(hours=1)}
        values.update(overrides)
        return transition_business_path(path, state, **values)

    def test_saved_a_investigating_crea_nueva_version(self):
        old = promote().business_path
        new = self.transition(old, BusinessPathState.INVESTIGATING)
        self.assertEqual(new.version, 2)
        self.assertEqual(new.supersedes_version, 1)
        self.assertEqual(old.state, BusinessPathState.SAVED)

    def test_pausa_y_reanudacion(self):
        saved = promote().business_path
        paused = self.transition(saved, BusinessPathState.PAUSED)
        resumed = self.transition(paused, BusinessPathState.INVESTIGATING, evaluated_at=NOW + timedelta(hours=2))
        self.assertEqual(paused.state, BusinessPathState.PAUSED)
        self.assertEqual(resumed.state, BusinessPathState.INVESTIGATING)

    def test_abandono_voluntario_cierra_y_no_invalida(self):
        path = promote().business_path
        closed = self.transition(
            path,
            BusinessPathState.CLOSED,
            reason="El usuario decidió abandonar el camino.",
        )
        self.assertEqual(closed.state, BusinessPathState.CLOSED)
        self.assertNotEqual(closed.state, BusinessPathState.INVALIDATED)

    def test_invalidacion_sin_evidencia_verificable_se_rechaza(self):
        with self.assertRaises(DomainValidationError):
            self.transition(
                promote().business_path, BusinessPathState.INVALIDATED
            )

    def test_evidencia_verificada_permite_invalidar(self):
        path = promote().business_path
        evidence = Result("result-1", "restricción comprobada", True, EvidenceType.DATA, "fuente", recorded_at=NOW)
        invalidated = self.transition(path, BusinessPathState.INVALIDATED, supporting_evidence=(evidence,))
        self.assertIn(evidence, invalidated.available_evidence)

    def test_restriccion_dura_verificada_permite_invalidar(self):
        path = promote().business_path
        evidence = Result(
            "result-hard-constraint",
            "restricción legal aplicable",
            True,
            EvidenceType.DATA,
            "fuente oficial",
            recorded_at=NOW,
        )
        invalidated = self.transition(
            path,
            BusinessPathState.INVALIDATED,
            reason="Una restricción legal verificada contradice el camino.",
            supporting_evidence=(evidence,),
        )
        self.assertEqual(invalidated.state, BusinessPathState.INVALIDATED)

    def test_missing_data_no_invalida(self):
        path = promote().business_path
        self.assertEqual(path.state, BusinessPathState.SAVED)
        self.assertIn("demanda", path.missing_evidence)

    def test_confianza_baja_no_invalida(self):
        path = promote(candidate(confidence=ConfidenceLevel.LOW)).business_path
        self.assertEqual(path.state, BusinessPathState.SAVED)

    def test_evidencia_y_contexto_historicos_no_mutan(self):
        old = promote().business_path
        evidence = Result("result-2", "hallazgo", False, EvidenceType.DATA, "fuente", recorded_at=NOW)
        new = self.transition(old, BusinessPathState.INVESTIGATING, supporting_evidence=(evidence,))
        self.assertEqual(old.available_evidence, ())
        self.assertEqual(new.context, old.context)

    def test_nuevo_presupuesto_reevalua_misma_ruta(self):
        shared = scenario()
        old = promote(
            candidate(
                path_scenario=shared,
                snapshot=context(available_budget=Money("100", "USD")),
            )
        ).business_path
        new_context = context(
            "2",
            NOW + timedelta(days=1),
            available_budget=Money("250", "USD"),
        )
        new = reevaluate_business_path(
            old,
            context=new_context,
            actor_id="user-1",
            reason="Presupuesto actualizado.",
            evaluated_at=NOW + timedelta(days=1),
        )
        self.assertEqual(new.business_path_id, old.business_path_id)
        self.assertEqual(new.version, 2)
        self.assertEqual(new.supersedes_version, 1)
        self.assertEqual(old.context.available_budget.amount, 100)
        self.assertEqual(new.context.available_budget.amount, 250)

    def test_nuevo_tiempo_reevalua_misma_ruta(self):
        shared = scenario()
        old = promote(
            candidate(
                path_scenario=shared,
                snapshot=context(available_time_hours_per_week=5),
            )
        ).business_path
        new = reevaluate_business_path(
            old,
            context=context(
                "2", NOW + timedelta(days=1), available_time_hours_per_week=15
            ),
            actor_id="user-1",
            reason="Tiempo actualizado.",
            evaluated_at=NOW + timedelta(days=1),
        )
        self.assertEqual(new.business_path_id, old.business_path_id)
        self.assertEqual(old.context.available_time_hours_per_week, 5)
        self.assertEqual(new.context.available_time_hours_per_week, 15)

    def test_reevaluacion_conserva_evidencia_actor_motivo_y_timestamps(self):
        old = promote(candidate(path_scenario=scenario())).business_path
        evidence = Result(
            "result-new", "evidencia nueva", True, EvidenceType.DATA,
            "fuente", recorded_at=NOW,
        )
        new = reevaluate_business_path(
            old,
            context=context("2", NOW + timedelta(days=1)),
            actor_id="analyst-1",
            reason="Nueva evaluación.",
            evaluated_at=NOW + timedelta(days=1),
            additional_evidence=(evidence,),
        )
        self.assertEqual(old.available_evidence, ())
        self.assertEqual(new.available_evidence, (evidence,))
        self.assertEqual(new.retained_by, "analyst-1")
        self.assertEqual(new.state_change_reason, "Nueva evaluación.")
        self.assertIsNotNone(new.last_evaluated_at.tzinfo)

    def test_reevaluacion_nunca_reemplaza_evidencia_historica(self):
        original = Result(
            "result-original",
            "evidencia original",
            True,
            EvidenceType.DATA,
            "fuente original",
            recorded_at=NOW,
        )
        source = replace(
            candidate(path_scenario=scenario()),
            available_evidence=(original,),
        )
        old = promote(source).business_path
        added = Result(
            "result-added",
            "evidencia nueva",
            True,
            EvidenceType.DATA,
            "fuente nueva",
            recorded_at=NOW + timedelta(days=1),
        )
        new = reevaluate_business_path(
            old,
            context=context("2", NOW + timedelta(days=1)),
            actor_id="analyst-1",
            reason="Se añadió evidencia.",
            evaluated_at=NOW + timedelta(days=1),
            additional_evidence=(added,),
        )
        self.assertEqual(old.available_evidence, (original,))
        self.assertEqual(new.available_evidence, (original, added))

    def test_timezone_es_obligatorio(self):
        with self.assertRaises(DomainValidationError):
            promote(promoted_at=datetime(2026, 8, 10))
        with self.assertRaises(DomainValidationError):
            self.transition(promote().business_path, BusinessPathState.PAUSED, evaluated_at=datetime(2026, 8, 10))

    def test_serializacion_completa_e_inmutable(self):
        result = promote()
        payload = result.to_dict()
        self.assertIsInstance(json.dumps(payload), str)
        payload["warnings"].append("externa")
        self.assertNotIn("externa", result.warnings)
        with self.assertRaises(FrozenInstanceError):
            result.business_path.state = BusinessPathState.CLOSED

    def test_transicion_no_permitida_se_rechaza(self):
        closed = self.transition(promote().business_path, BusinessPathState.CLOSED)
        with self.assertRaises(DomainValidationError):
            self.transition(closed, BusinessPathState.INVESTIGATING, evaluated_at=NOW + timedelta(hours=2))


if __name__ == "__main__":
    unittest.main()
