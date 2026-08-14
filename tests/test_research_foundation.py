import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path

from application.business_path_service import promote_candidate_business_path
from application.research_service import assess_business_path_research
from domain.contracts import CandidateBusinessPath, PathAssessment
from domain.entities import EvidenceRecord, Investigation, ResearchFinding
from domain.enums import (
    CandidatePathState, ConfidenceLevel, ConflictResolutionStatus, EvidenceType,
    FreshnessStatus, InvestigationStatus, PathPromotionAction, ResearchCategory,
    ResearchQuestionStatus, VerificationStatus,
)
from domain.exceptions import DomainValidationError
from domain.value_objects import GoalContextSnapshot, Money, Region, ResearchNeed, ResearchQuestion


NOW = datetime(2026, 8, 13, 12, tzinfo=timezone.utc)
PATH_ID_SOURCE = "11111111-1111-4111-8111-111111111111"
EVIDENCE_1 = "22222222-2222-4222-8222-222222222222"
EVIDENCE_2 = "33333333-3333-4333-8333-333333333333"


def business_path(missing=("demanda", "competencia", "proveedor", "costos finales")):
    context = GoalContextSnapshot(
        "goal-1", NOW, "1", available_budget=Money("0", "USD"),
        available_time_hours_per_week=0, region=Region("US"),
    )
    candidate = CandidateBusinessPath(
        PATH_ID_SOURCE, "goal-1", context,
        PathAssessment((), ConfidenceLevel.LOW, "1"),
        CandidatePathState.INCOMPLETE, ConfidenceLevel.LOW, "1",
        missing_evidence=missing,
    )
    return promote_candidate_business_path(
        candidate, action=PathPromotionAction.SAVE,
        actor_id="user-1", promoted_at=NOW,
    ).business_path


def evidence(identifier=EVIDENCE_1, *, category=ResearchCategory.DEMAND,
             kind=EvidenceType.ESTIMATE, value=None,
             freshness=FreshnessStatus.CURRENT,
             verification=VerificationStatus.UNVERIFIED,
             source="usuario", observed_at=NOW, retrieved_at=NOW,
             limitations=()):
    path = business_path()
    return EvidenceRecord(
        identifier, "business_path", path.business_path_id, category, kind,
        value or {"value": 100}, source, observed_at, retrieved_at,
        freshness, verification, ConfidenceLevel.MEDIUM, "1",
        region=Region("US"), limitations=limitations,
    )


def assess(records=(), previous=None, path=None, at=NOW):
    return assess_business_path_research(
        business_path=path or business_path(), evidence=records,
        assessed_at=at, previous_assessment=previous,
    )


class InvestigationTests(unittest.TestCase):
    def test_investigation_valida_y_serializable(self):
        result = assess()
        self.assertIsInstance(result.investigation, Investigation)
        json.dumps(result.investigation.to_dict())

    def test_investigation_rechaza_fechas_sin_timezone(self):
        item = assess().investigation
        with self.assertRaises(DomainValidationError):
            Investigation(item.investigation_id, "business_path", item.subject_id,
                          InvestigationStatus.PENDING, (), (), (),
                          datetime(2026, 1, 1), NOW, 1)

    def test_investigacion_versionada_conserva_identidad(self):
        first = assess()
        second = assess((evidence(),), previous=first, at=NOW + timedelta(days=1))
        self.assertEqual(first.investigation.investigation_id, second.investigation.investigation_id)
        self.assertEqual(second.investigation.version, 2)
        self.assertEqual(second.investigation.supersedes_version, 1)
        self.assertEqual(first.evidence, ())

    def test_investigacion_es_inmutable(self):
        item = assess().investigation
        with self.assertRaises(FrozenInstanceError):
            item.status = InvestigationStatus.VERIFIED


class ResearchNeedQuestionTests(unittest.TestCase):
    def test_need_es_determinista(self):
        first = assess().needs[0]
        second = assess(at=NOW + timedelta(hours=2)).needs[0]
        self.assertEqual(first.need_id, second.need_id)

    def test_question_es_determinista_y_auditable(self):
        first = assess().questions[0]
        second = assess(at=NOW + timedelta(hours=2)).questions[0]
        self.assertEqual(first.question_id, second.question_id)
        self.assertIn("verificable", first.question)

    def test_blocking_no_invalida_business_path(self):
        path = business_path()
        result = assess(path=path)
        self.assertTrue(all(item.blocking for item in result.needs))
        self.assertEqual(path.state.value, "saved")

    def test_multiples_needs_coexisten(self):
        result = assess()
        self.assertEqual({item.category for item in result.needs}, {
            ResearchCategory.DEMAND, ResearchCategory.COMPETITION,
            ResearchCategory.SUPPLIER, ResearchCategory.COSTS,
        })

    def test_presupuesto_y_tiempo_cero_son_datos_conocidos(self):
        path = business_path()
        self.assertEqual(path.context.available_budget.amount, 0)
        self.assertEqual(path.context.available_time_hours_per_week, 0)

    def test_need_no_contiene_score_global(self):
        payload = assess().needs[0].to_dict()
        self.assertNotIn("score", payload)
        self.assertNotIn("probability", payload)

    def test_need_y_question_rechazan_ids_falsos(self):
        item = assess().needs[0]
        with self.assertRaises(DomainValidationError):
            ResearchNeed(item.subject_type, item.subject_id, item.category,
                         item.reason, item.importance, item.blocking,
                         item.required_evidence_types, need_id="fake")
        question = assess().questions[0]
        with self.assertRaises(DomainValidationError):
            ResearchQuestion(question.research_need_id, question.question,
                             question.subject_type, question.subject_id,
                             question.expected_evidence, question.status,
                             question_id="fake")


class EvidenceRecordTests(unittest.TestCase):
    def test_data_estimate_assumption_se_conservan(self):
        for kind in EvidenceType:
            with self.subTest(kind=kind):
                self.assertEqual(evidence(kind=kind).evidence_type, kind)

    def test_supuesto_de_usuario_nunca_es_data(self):
        item = evidence(kind=EvidenceType.ASSUMPTION, value={"units_per_month": 100})
        self.assertEqual(item.to_dict()["evidence_type"], "supuesto")

    def test_fuente_desconocida_debe_ser_explicita(self):
        item = evidence(source="desconocida")
        self.assertEqual(item.source, "desconocida")
        with self.assertRaises(DomainValidationError):
            evidence(source=" ")

    def test_verification_y_freshness_son_independientes(self):
        item = evidence(freshness=FreshnessStatus.EXPIRED,
                        verification=VerificationStatus.VERIFIED)
        self.assertEqual(item.freshness, FreshnessStatus.EXPIRED)
        self.assertEqual(item.verification_status, VerificationStatus.VERIFIED)

    def test_fechas_sin_timezone_se_rechazan(self):
        with self.assertRaises(DomainValidationError):
            evidence(observed_at=datetime(2026, 1, 1))
        with self.assertRaises(DomainValidationError):
            evidence(retrieved_at=datetime(2026, 1, 1))

    def test_identidad_historica_es_independiente(self):
        first = evidence(EVIDENCE_1)
        second = evidence(EVIDENCE_2, retrieved_at=NOW + timedelta(days=1))
        self.assertNotEqual(first, second)
        self.assertEqual(first.value, second.value)

    def test_valor_cero_no_se_confunde_con_ausencia(self):
        item = evidence(value={"cost": 0}, category=ResearchCategory.COSTS)
        self.assertEqual(item.value.to_dict()["cost"], 0)

    def test_evidence_es_inmutable_y_serializa_copia(self):
        source = {"nested": {"values": [1, 2]}}
        item = evidence(value=source)
        source["nested"]["values"].append(3)
        payload = item.to_dict()
        payload["value"]["nested"]["values"].append(4)
        self.assertEqual(item.value.to_dict(), {"nested": {"values": [1, 2]}})
        with self.assertRaises(FrozenInstanceError):
            item.source = "otro"

    def test_metadata_sensible_directa_y_anidada_se_rechaza(self):
        for value in ({"ACCESS_TOKEN": "x"}, {"auth": {"client-secret": "x"}}, {"user": {"E-MAIL": "x"}}):
            with self.subTest(value=value), self.assertRaises(DomainValidationError):
                evidence(value=value)
        with self.assertRaises(DomainValidationError):
            EvidenceRecord(
                EVIDENCE_1, "business_path", business_path().business_path_id,
                ResearchCategory.DEMAND, EvidenceType.DATA, {"value": 1},
                "fuente", NOW, NOW, FreshnessStatus.CURRENT,
                VerificationStatus.UNVERIFIED, ConfidenceLevel.LOW, "1",
                source_reference="https://example.test/?access_token=secret",
            )


class FindingConflictTests(unittest.TestCase):
    def test_finding_conserva_evidence_ids_y_no_es_data(self):
        result = assess((evidence(),))
        finding = result.findings[0]
        self.assertEqual(finding.evidence_ids, (EVIDENCE_1,))
        self.assertNotEqual(finding.interpretation_type, EvidenceType.DATA)

    def test_finding_sin_evidencia_debe_ser_hipotesis(self):
        investigation_id = assess().investigation.investigation_id
        finding_id = "44444444-4444-4444-8444-444444444444"
        item = ResearchFinding(finding_id, investigation_id, "Hipótesis", (),
                               EvidenceType.ASSUMPTION, ConfidenceLevel.LOW,
                               ("Sin evidencia.",), NOW, "1")
        self.assertEqual(item.interpretation_type, EvidenceType.ASSUMPTION)
        with self.assertRaises(DomainValidationError):
            ResearchFinding(finding_id, investigation_id, "Interpretación", (),
                            EvidenceType.ESTIMATE, ConfidenceLevel.LOW, (), NOW, "1")

    def test_finding_nunca_acepta_data(self):
        investigation_id = assess().investigation.investigation_id
        with self.assertRaises(DomainValidationError):
            ResearchFinding("44444444-4444-4444-8444-444444444444",
                            investigation_id, "Hecho aparente", (EVIDENCE_1,),
                            EvidenceType.DATA, ConfidenceLevel.HIGH, (), NOW, "1")

    def test_evidencia_contradictoria_permanece_y_conflicto_visible(self):
        first = evidence(EVIDENCE_1, value={"moq": 100}, category=ResearchCategory.SUPPLIER)
        second = evidence(EVIDENCE_2, value={"moq": 250}, category=ResearchCategory.SUPPLIER)
        result = assess((first, second))
        self.assertEqual(len(result.evidence), 2)
        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(result.conflicts[0].resolution_status, ConflictResolutionStatus.OPEN)
        self.assertEqual(result.confidence, ConfidenceLevel.LOW)

    def test_conflicto_no_selecciona_ganador(self):
        result = assess((evidence(EVIDENCE_1, value={"moq": 100}, category=ResearchCategory.SUPPLIER), evidence(EVIDENCE_2, value={"moq": 250}, category=ResearchCategory.SUPPLIER)))
        payload = result.conflicts[0].to_dict()
        self.assertNotIn("winner", payload)
        self.assertNotIn("selected_evidence", payload)


class ResearchServiceTests(unittest.TestCase):
    def test_business_path_sin_datos_genera_needs_y_confianza_baja(self):
        result = assess()
        self.assertEqual(result.confidence, ConfidenceLevel.LOW)
        self.assertEqual(len(result.needs), 4)
        self.assertEqual(result.investigation.status, InvestigationStatus.PENDING)

    def test_evidencia_parcial_no_se_presenta_verificada(self):
        result = assess((evidence(kind=EvidenceType.ESTIMATE),))
        self.assertEqual(result.unverified_information, (f"demand:{EVIDENCE_1}",))
        self.assertFalse(result.verified_information)
        self.assertTrue(any(item.category is ResearchCategory.COMPETITION for item in result.needs))
        self.assertTrue(any(item.category is ResearchCategory.DEMAND and item.known_information for item in result.needs))

    def test_evidencia_verificada_resuelve_need_sin_promesa(self):
        record = evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED)
        result = assess((record,))
        self.assertFalse(any(item.category is ResearchCategory.DEMAND for item in result.needs))
        self.assertEqual(result.verified_information, (f"demand:{EVIDENCE_1}",))
        demand_question = next(
            item for item in result.questions if "demanda" in item.question
        )
        self.assertEqual(demand_question.status, ResearchQuestionStatus.VERIFIED)
        self.assertNotIn("demand", result.missing_information)
        self.assertNotIn(demand_question.question, " ".join(result.next_research_steps))
        self.assertNotIn("éxito", json.dumps(result.to_dict(), ensure_ascii=False).lower())

    def test_evidencia_vencida_permanece_y_solicita_actualizacion(self):
        record = evidence(kind=EvidenceType.DATA, freshness=FreshnessStatus.EXPIRED,
                          verification=VerificationStatus.VERIFIED)
        result = assess((record,))
        self.assertEqual(result.evidence, (record,))
        self.assertEqual(result.stale_information, (f"demand:{EVIDENCE_1}",))
        self.assertTrue(any(item.category is ResearchCategory.DEMAND for item in result.needs))

    def test_evidencia_vigente_y_vencida_coexisten(self):
        old = evidence(EVIDENCE_1, freshness=FreshnessStatus.EXPIRED)
        new = evidence(EVIDENCE_2, retrieved_at=NOW + timedelta(days=1))
        result = assess((old, new))
        self.assertEqual(len(result.evidence), 2)
        self.assertTrue(result.stale_information)
        self.assertEqual(result.conflicts, ())

    def test_nueva_evidencia_no_borra_anterior(self):
        first = assess((evidence(EVIDENCE_1),))
        second = assess((evidence(EVIDENCE_2, retrieved_at=NOW + timedelta(days=1)),), previous=first, at=NOW + timedelta(days=1))
        self.assertEqual({item.evidence_id for item in second.evidence}, {EVIDENCE_1, EVIDENCE_2})

    def test_business_path_no_cambia(self):
        path = business_path()
        before = path.to_dict()
        assess((evidence(),), path=path)
        self.assertEqual(path.to_dict(), before)

    def test_opportunity_y_scenario_no_se_mutan(self):
        from tests.test_business_path_service import scenario as build_scenario

        related_scenario = build_scenario()
        related_opportunity = related_scenario.opportunity
        before_scenario = related_scenario.to_dict()
        before_opportunity = related_opportunity.to_dict()
        assess_business_path_research(
            business_path=business_path(), evidence=(), assessed_at=NOW,
            opportunity=related_opportunity, scenario=related_scenario,
        )
        self.assertEqual(related_scenario.to_dict(), before_scenario)
        self.assertEqual(related_opportunity.to_dict(), before_opportunity)

    def test_input_determinista_produce_misma_semantica(self):
        first = assess((evidence(),))
        second = assess((evidence(),))
        self.assertEqual(first.investigation.investigation_id, second.investigation.investigation_id)
        self.assertEqual([x.need_id for x in first.needs], [x.need_id for x in second.needs])
        self.assertEqual([x.question_id for x in first.questions], [x.question_id for x in second.questions])

    def test_evidencia_de_otro_sujeto_se_rechaza(self):
        item = evidence()
        foreign = EvidenceRecord(EVIDENCE_2, "business_path", "otro", item.category,
                                 item.evidence_type, item.value, item.source,
                                 NOW, NOW, item.freshness, item.verification_status,
                                 item.confidence, "1")
        with self.assertRaises(DomainValidationError):
            assess((foreign,))

    def test_assessment_no_contiene_decision_score_ranking_probability(self):
        payload = assess().to_dict()
        for forbidden in ("winner", "ranking", "probability_of_success", "opportunity_score", "investment_recommendation"):
            self.assertNotIn(forbidden, payload)

    def test_assessment_es_profunda_inmutable_y_serializa_copias(self):
        result = assess((evidence(),))
        payload = result.to_dict()
        json.dumps(payload)
        payload["evidence"][0]["value"]["value"] = 999
        payload["missing_information"].clear()
        self.assertEqual(result.evidence[0].value.to_dict()["value"], 100)
        self.assertTrue(result.missing_information)
        with self.assertRaises(FrozenInstanceError):
            result.confidence = ConfidenceLevel.HIGH


class ArchitectureProtectionTests(unittest.TestCase):
    def test_domain_no_importa_capas_externas(self):
        root = Path(__file__).resolve().parents[1] / "domain"
        text = "\n".join(path.read_text() for path in root.rglob("*.py")).lower()
        for forbidden in ("from application", "import application", "streamlit", "requests", "neo4j", "networkx"):
            self.assertNotIn(forbidden, text)

    def test_service_no_contiene_apis_llm_scraping_o_formulas(self):
        text = (Path(__file__).resolve().parents[1] / "application" / "research_service.py").read_text().lower()
        for forbidden in ("requests", "http", "scrap", "openai", "llm", "calculate_roi", "calcular_rentabilidad", "opportunity_score"):
            self.assertNotIn(forbidden, text)

    def test_motores_y_archivos_protegidos_no_son_importados(self):
        text = (Path(__file__).resolve().parents[1] / "application" / "research_service.py").read_text().lower()
        for forbidden in ("decision_service", "opportunity_service", "marketplace_service", "business_model_service", "scout", "calculator"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
