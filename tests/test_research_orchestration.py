import json
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from application.research_models import (
    EvidenceAccess, EvidenceVisibility, ResearchCapabilityRequest,
    ResearchCapabilityResultStatus, ResearchExecutionContext, ResearchFailure,
    ResearchPlan, ResearchPriority, ResearchTask, ResearchTaskDependency,
    ResearchTaskState,
)
from application.research_orchestration_service import (
    create_research_plan, execute_research_plan, parallelizable_groups,
    validate_task_dag,
)
from domain.enums import EvidenceType, FreshnessStatus, ResearchCategory, VerificationStatus
from domain.exceptions import DomainValidationError
from domain.value_objects import Region
from tests.fakes.research_capability import FakeResearchCapability
from tests.test_research_foundation import EVIDENCE_1, NOW, assess, evidence


CTX = ResearchExecutionContext("project-a", "request-1", NOW, Region("US"))


def capabilities(mode="success", categories=None):
    categories = categories or tuple(ResearchCategory)
    return (FakeResearchCapability("fake-research", categories, region_codes=("US",), mode=mode),)


def plan_for(assessment=None, caps=None, accesses=(), at=NOW):
    return create_research_plan(
        assessment=assessment or assess(), capabilities=caps or capabilities(),
        execution_context=CTX, evidence_access=accesses, created_at=at,
    )


class ResearchModelTests(unittest.TestCase):
    def test_todos_los_estados_contractuales_existen(self):
        self.assertEqual({item.value for item in ResearchTaskState}, {
            "pending", "ready", "blocked", "running", "completed",
            "partial", "failed", "skipped_reused",
        })

    def test_prioridad_es_categoria_sin_peso(self):
        self.assertEqual({item.value for item in ResearchPriority}, {"blocking", "high", "normal", "low"})

    def test_access_privado_requiere_scope(self):
        with self.assertRaises(DomainValidationError):
            EvidenceAccess(EVIDENCE_1, EvidenceVisibility.PRIVATE)

    def test_access_publico_no_requiere_scope(self):
        item = EvidenceAccess(EVIDENCE_1, EvidenceVisibility.PUBLIC_REUSABLE)
        self.assertIsNone(item.owner_scope_id)

    def test_task_valida_serializable_e_inmutable(self):
        plan = plan_for()
        task = plan.tasks[0]
        json.dumps(task.to_dict())
        with self.assertRaises(FrozenInstanceError):
            task.state = ResearchTaskState.FAILED

    def test_task_id_determinista_y_timestamp_irrelevante(self):
        first = plan_for(at=NOW).tasks[0]
        second = plan_for(at=NOW + timedelta(hours=1)).tasks[0]
        self.assertEqual(first.task_id, second.task_id)

    def test_plan_id_determinista_y_timestamp_irrelevante(self):
        first = plan_for(at=NOW)
        second = plan_for(at=NOW + timedelta(hours=2))
        self.assertEqual(first.plan_id, second.plan_id)

    def test_orden_de_needs_no_altera_plan(self):
        assessment = assess()
        reversed_assessment = replace(assessment, needs=tuple(reversed(assessment.needs)), questions=tuple(reversed(assessment.questions)))
        self.assertEqual(plan_for(assessment).plan_id, plan_for(reversed_assessment).plan_id)

    def test_plan_serializa_copia_profunda(self):
        plan = plan_for()
        payload = plan.to_dict()
        payload["tasks"].clear()
        self.assertTrue(plan.tasks)

    def test_fechas_sin_timezone_rechazadas(self):
        with self.assertRaises(DomainValidationError):
            ResearchExecutionContext("scope", "id", datetime(2026, 1, 1))

    def test_safe_context_rechaza_secreto_directo_y_anidado(self):
        for context in ({"access_token": "x"}, {"nested": {"client_secret": "x"}}):
            with self.subTest(context=context), self.assertRaises(DomainValidationError):
                ResearchFailure("timeout", "x", True, "fake", NOW, context)

    def test_failure_message_rechaza_marcadores_de_secretos(self):
        with self.assertRaises(DomainValidationError):
            ResearchFailure("timeout", "authorization: bearer secret", True, "fake", NOW)

    def test_capability_request_serializa_copia(self):
        task = plan_for().tasks[0]
        request = ResearchCapabilityRequest(task.task_id, task.category, "Pregunta", task.subject_type, task.subject_id, CTX, task.region, task.marketplace_id, task.time_scope, ("evidence-1",))
        payload = request.to_dict()
        payload["known_evidence_ids"].clear()
        self.assertEqual(request.known_evidence_ids, ("evidence-1",))

    def test_failure_no_es_evidence(self):
        failure = ResearchFailure("timeout", "x", True, "fake", NOW)
        self.assertNotIn("evidence", failure.to_dict())

    def test_result_failed_requiere_failure(self):
        from application.research_models import ResearchCapabilityResult
        with self.assertRaises(DomainValidationError):
            ResearchCapabilityResult("task", ResearchCapabilityResultStatus.FAILED, "fake", NOW)

    def test_result_success_rechaza_failure(self):
        from application.research_models import ResearchCapabilityResult
        failure = ResearchFailure("timeout", "x", True, "fake", NOW)
        with self.assertRaises(DomainValidationError):
            ResearchCapabilityResult("task", ResearchCapabilityResultStatus.SUCCESS, "fake", NOW, failure=failure)

    def test_no_data_no_afirma_ausencia_comercial(self):
        cap = capabilities("no_data")[0]
        plan = plan_for(caps=(cap,))
        assessment = execute_research_plan(plan=plan, assessment=assess(), capabilities=(cap,), execution_context=CTX, generated_at=NOW)
        text = json.dumps(assessment.to_dict(), ensure_ascii=False).lower()
        self.assertIn("no obtuvo evidencia suficiente", text)
        self.assertNotIn("no existen proveedores", text)


class PlanningTests(unittest.TestCase):
    def test_sin_evidencia_tareas_ready(self):
        self.assertTrue(all(task.state is ResearchTaskState.READY for task in plan_for().tasks))

    def test_capability_incompatible_bloquea(self):
        cap = FakeResearchCapability("other", (ResearchCategory.LOGISTICS,))
        plan = plan_for(caps=(cap,))
        self.assertTrue(all(task.state is ResearchTaskState.BLOCKED for task in plan.tasks))

    def test_capability_region_incompatible_bloquea(self):
        cap = FakeResearchCapability("other-region", tuple(ResearchCategory), region_codes=("CA",))
        self.assertTrue(all(task.state is ResearchTaskState.BLOCKED for task in plan_for(caps=(cap,)).tasks))

    def test_prioridad_bloqueante_tiene_explicacion(self):
        task = plan_for().tasks[0]
        self.assertEqual(task.priority, ResearchPriority.BLOCKING)
        self.assertIn("bloquea", task.priority_reason)

    def test_data_verified_current_se_reutiliza(self):
        record = evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED)
        assessment = assess((record,))
        # Research Foundation removes a satisfied need; reintroduce its original need/question
        baseline = assess()
        assessment = replace(assessment, needs=baseline.needs, questions=baseline.questions)
        access = EvidenceAccess(record.evidence_id, EvidenceVisibility.PROJECT_SCOPED, "project-a")
        demand = next(task for task in plan_for(assessment, accesses=(access,)).tasks if task.category is ResearchCategory.DEMAND)
        self.assertEqual(demand.state, ResearchTaskState.SKIPPED_REUSED)
        self.assertEqual(demand.reusable_evidence_ids, (record.evidence_id,))

    def test_estimate_assumption_y_expired_no_satisfacen(self):
        variants = (
            evidence(kind=EvidenceType.ESTIMATE, verification=VerificationStatus.VERIFIED),
            evidence(kind=EvidenceType.ASSUMPTION, verification=VerificationStatus.VERIFIED),
            evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED, freshness=FreshnessStatus.EXPIRED),
        )
        baseline = assess()
        for record in variants:
            with self.subTest(record=record.evidence_type, freshness=record.freshness):
                assessed = replace(assess((record,)), needs=baseline.needs, questions=baseline.questions)
                access = EvidenceAccess(record.evidence_id, EvidenceVisibility.PUBLIC_REUSABLE)
                demand = next(task for task in plan_for(assessed, accesses=(access,)).tasks if task.category is ResearchCategory.DEMAND)
                self.assertNotEqual(demand.state, ResearchTaskState.SKIPPED_REUSED)

    def test_region_y_marketplace_distintos_no_reutilizan(self):
        baseline = assess()
        question = next(item for item in baseline.questions if item.research_need_id == baseline.needs[0].need_id)
        record = evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED)
        foreign_region = replace(record, region=Region("CA"))
        assessed = replace(assess((foreign_region,)), needs=baseline.needs, questions=baseline.questions)
        access = EvidenceAccess(record.evidence_id, EvidenceVisibility.PUBLIC_REUSABLE)
        task = next(item for item in plan_for(assessed, accesses=(access,)).tasks if item.research_need_id == question.research_need_id)
        self.assertNotEqual(task.state, ResearchTaskState.SKIPPED_REUSED)

    def test_evidencia_privada_no_cruza_scope(self):
        record = evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED)
        baseline = assess()
        assessed = replace(assess((record,)), needs=baseline.needs, questions=baseline.questions)
        access = EvidenceAccess(record.evidence_id, EvidenceVisibility.PRIVATE, "project-b")
        self.assertFalse(any(task.state is ResearchTaskState.SKIPPED_REUSED for task in plan_for(assessed, accesses=(access,)).tasks))

    def test_evidencia_privada_mismo_scope_si_reutiliza(self):
        record = evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED)
        baseline = assess()
        assessed = replace(assess((record,)), needs=baseline.needs, questions=baseline.questions)
        access = EvidenceAccess(record.evidence_id, EvidenceVisibility.PRIVATE, "project-a")
        self.assertTrue(any(task.state is ResearchTaskState.SKIPPED_REUSED for task in plan_for(assessed, accesses=(access,)).tasks))

    def test_project_scoped_no_cruza_proyecto(self):
        record = evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED)
        baseline = assess()
        assessed = replace(assess((record,)), needs=baseline.needs, questions=baseline.questions)
        access = EvidenceAccess(record.evidence_id, EvidenceVisibility.PROJECT_SCOPED, "project-b")
        self.assertFalse(any(task.state is ResearchTaskState.SKIPPED_REUSED for task in plan_for(assessed, accesses=(access,)).tasks))

    def test_public_reusable_cruza_scope(self):
        record = evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED)
        baseline = assess()
        assessed = replace(assess((record,)), needs=baseline.needs, questions=baseline.questions)
        access = EvidenceAccess(record.evidence_id, EvidenceVisibility.PUBLIC_REUSABLE)
        self.assertTrue(any(task.state is ResearchTaskState.SKIPPED_REUSED for task in plan_for(assessed, accesses=(access,)).tasks))

    def test_periodo_distinto_no_se_reutiliza(self):
        record = evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED)
        baseline = assess()
        demand_need = next(item for item in baseline.needs if item.category is ResearchCategory.DEMAND)
        updated_questions = tuple(
            replace(item, time_scope="ultimos-30-dias", question_id=None)
            if item.research_need_id == demand_need.need_id else item
            for item in baseline.questions
        )
        assessed = replace(assess((record,)), needs=baseline.needs, questions=updated_questions)
        access = EvidenceAccess(record.evidence_id, EvidenceVisibility.PUBLIC_REUSABLE, time_scope="otro-periodo")
        demand = next(item for item in plan_for(assessed, accesses=(access,)).tasks if item.category is ResearchCategory.DEMAND)
        self.assertNotEqual(demand.state, ResearchTaskState.SKIPPED_REUSED)

    def test_marketplace_distinto_no_se_reutiliza(self):
        record = replace(
            evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED),
            marketplace_id="market-b",
        )
        baseline = assess()
        demand_need = next(item for item in baseline.needs if item.category is ResearchCategory.DEMAND)
        updated_questions = tuple(
            replace(item, marketplace_id="market-a", question_id=None)
            if item.research_need_id == demand_need.need_id else item
            for item in baseline.questions
        )
        assessed = replace(assess((record,)), needs=baseline.needs, questions=updated_questions)
        access = EvidenceAccess(record.evidence_id, EvidenceVisibility.PUBLIC_REUSABLE)
        demand = next(item for item in plan_for(assessed, accesses=(access,)).tasks if item.category is ResearchCategory.DEMAND)
        self.assertNotEqual(demand.state, ResearchTaskState.SKIPPED_REUSED)

    def test_nueva_evidencia_suficiente_elimina_trabajo_redundante(self):
        before = plan_for(assess())
        record = evidence(kind=EvidenceType.DATA, verification=VerificationStatus.VERIFIED)
        after_assessment = assess((record,))
        after = plan_for(after_assessment)
        self.assertGreater(len(before.tasks), len(after.tasks))
        self.assertFalse(any(item.category is ResearchCategory.DEMAND for item in after.tasks))

    def test_unverified_no_se_reutiliza(self):
        record = evidence(kind=EvidenceType.DATA, verification=VerificationStatus.UNVERIFIED)
        baseline = assess()
        assessed = replace(assess((record,)), needs=baseline.needs, questions=baseline.questions)
        access = EvidenceAccess(record.evidence_id, EvidenceVisibility.PUBLIC_REUSABLE)
        self.assertFalse(any(task.state is ResearchTaskState.SKIPPED_REUSED for task in plan_for(assessed, accesses=(access,)).tasks))

    def test_conflicto_activo_impide_reutilizacion(self):
        from tests.test_research_foundation import EVIDENCE_2
        first = evidence(EVIDENCE_1, kind=EvidenceType.DATA, value={"value": 1}, verification=VerificationStatus.VERIFIED)
        second = evidence(EVIDENCE_2, kind=EvidenceType.DATA, value={"value": 2}, verification=VerificationStatus.VERIFIED)
        baseline = assess()
        assessed = assess((first, second))
        assessed = replace(assessed, needs=baseline.needs, questions=baseline.questions)
        accesses = (EvidenceAccess(first.evidence_id, EvidenceVisibility.PUBLIC_REUSABLE), EvidenceAccess(second.evidence_id, EvidenceVisibility.PUBLIC_REUSABLE))
        self.assertFalse(any(task.state is ResearchTaskState.SKIPPED_REUSED for task in plan_for(assessed, accesses=accesses).tasks))

    def test_cambio_material_de_needs_cambia_plan(self):
        baseline = assess()
        reduced = replace(baseline, needs=baseline.needs[:-1], questions=baseline.questions[:-1])
        self.assertNotEqual(plan_for(baseline).plan_id, plan_for(reduced).plan_id)

    def test_idempotencia(self):
        self.assertEqual(plan_for().to_dict(), plan_for().to_dict())

    def test_no_score_ranking_winner_recommendation(self):
        payload = json.dumps(plan_for().to_dict()).lower()
        for forbidden in ("score", "ranking", "winner", "recommendation"):
            self.assertNotIn(forbidden, payload)


class DagTests(unittest.TestCase):
    def test_dag_valido_y_paralelizable(self):
        plan = plan_for()
        self.assertEqual(len(parallelizable_groups(plan)), 1)
        self.assertEqual(len(parallelizable_groups(plan)[0]), 4)

    def test_dependencia_inexistente(self):
        tasks = plan_for().tasks
        dep = ResearchTaskDependency(tasks[0].task_id, "missing", "x")
        with self.assertRaises(DomainValidationError):
            validate_task_dag(tasks, (dep,))

    def test_self_dependency(self):
        task_id = plan_for().tasks[0].task_id
        with self.assertRaises(DomainValidationError):
            ResearchTaskDependency(task_id, task_id, "x")

    def test_ciclo(self):
        tasks = plan_for().tasks[:2]
        deps = (ResearchTaskDependency(tasks[0].task_id, tasks[1].task_id, "x"), ResearchTaskDependency(tasks[1].task_id, tasks[0].task_id, "y"))
        with self.assertRaises(DomainValidationError):
            validate_task_dag(tasks, deps)

    def test_dependencia_duplicada(self):
        tasks = plan_for().tasks[:2]
        dep = ResearchTaskDependency(tasks[0].task_id, tasks[1].task_id, "x")
        with self.assertRaises(DomainValidationError):
            validate_task_dag(tasks, (dep, dep))

    def test_dependencia_crea_capas_paralelas(self):
        base = plan_for()
        dep = ResearchTaskDependency(base.tasks[0].task_id, base.tasks[1].task_id, "La segunda requiere contexto de la primera.")
        layered = plan_for(caps=capabilities())
        layered = ResearchPlan(layered.investigation_id, layered.tasks, (dep,), layered.reusable_evidence, layered.missing_context, layered.warnings, layered.created_at, layered.plan_version, layered.business_path_id)
        groups = parallelizable_groups(layered)
        self.assertEqual(len(groups), 2)
        self.assertIn(base.tasks[1].task_id, groups[1])

    def test_orden_topologico_es_determinista(self):
        plan = plan_for()
        self.assertEqual(validate_task_dag(plan.tasks, ()), tuple(sorted(task.task_id for task in plan.tasks)))

    def test_orden_de_tasks_no_altera_plan_ni_grupos(self):
        base = plan_for()
        reversed_plan = ResearchPlan(base.investigation_id, tuple(reversed(base.tasks)), tuple(reversed(base.dependencies)), base.reusable_evidence, base.missing_context, base.warnings, base.created_at, base.plan_version, base.business_path_id)
        self.assertEqual(base.plan_id, reversed_plan.plan_id)
        self.assertEqual(parallelizable_groups(base), parallelizable_groups(reversed_plan))


class ExecutionTests(unittest.TestCase):
    def execute(self, mode="success"):
        cap = capabilities(mode)[0]
        assessment = assess()
        plan = plan_for(assessment, (cap,))
        return execute_research_plan(plan=plan, assessment=assessment, capabilities=(cap,), execution_context=CTX, generated_at=NOW)

    def test_success_conserva_evidencia(self):
        result = self.execute()
        self.assertEqual(len(result.completed_tasks), 4)
        self.assertEqual(len(result.evidence_obtained), 4)
        self.assertEqual(result.status, "completed")

    def test_partial_conserva_evidencia(self):
        result = self.execute("partial")
        self.assertEqual(len(result.partial_tasks), 4)
        self.assertEqual(len(result.evidence_obtained), 4)
        self.assertEqual(result.status, "partial")

    def test_no_data_deja_need_sin_resolver(self):
        result = self.execute("no_data")
        self.assertTrue(result.no_data_tasks)
        self.assertFalse(result.partial_tasks)
        self.assertFalse(result.evidence_obtained)
        self.assertTrue(result.missing_information)

    def test_partial_y_no_data_no_colapsan(self):
        partial = self.execute("partial")
        no_data = self.execute("no_data")
        self.assertTrue(partial.partial_tasks)
        self.assertFalse(partial.no_data_tasks)
        self.assertTrue(no_data.no_data_tasks)
        self.assertFalse(no_data.partial_tasks)

    def test_timeout_y_unavailable_son_fallos_tecnicos(self):
        for mode in ("timeout", "unavailable", "recoverable_failure", "fatal_failure"):
            with self.subTest(mode=mode):
                result = self.execute(mode)
                self.assertEqual(len(result.failed_tasks), 4)
                self.assertFalse(result.evidence_obtained)
                self.assertEqual(result.failures[0].retryable, mode != "fatal_failure")

    def test_fallo_tecnico_no_crea_evidencia_negativa(self):
        result = self.execute("timeout")
        payload = json.dumps(result.to_dict(), ensure_ascii=False).lower()
        self.assertFalse(result.evidence_obtained)
        self.assertNotIn("no hay demanda", payload)

    def test_evidencia_expirada_permanece_visible_como_stale(self):
        def expired(request, now):
            return evidence(category=request.category, kind=EvidenceType.DATA, freshness=FreshnessStatus.EXPIRED, verification=VerificationStatus.VERIFIED)
        cap = FakeResearchCapability("expired", tuple(ResearchCategory), region_codes=("US",), evidence_factory=expired)
        assessment = assess()
        plan = plan_for(assessment, (cap,))
        result = execute_research_plan(plan=plan, assessment=assessment, capabilities=(cap,), execution_context=CTX, generated_at=NOW)
        self.assertTrue(result.evidence_obtained)
        self.assertTrue(all(item.status.value == "stale" for item in result.coverage))

    def test_evidencia_no_verificada_permanece_visible(self):
        def unverified(request, now):
            return evidence(category=request.category, kind=EvidenceType.DATA, verification=VerificationStatus.UNVERIFIED)
        cap = FakeResearchCapability("unverified", tuple(ResearchCategory), region_codes=("US",), evidence_factory=unverified)
        assessment = assess()
        plan = plan_for(assessment, (cap,))
        result = execute_research_plan(plan=plan, assessment=assessment, capabilities=(cap,), execution_context=CTX, generated_at=NOW)
        self.assertTrue(result.evidence_obtained)
        self.assertTrue(all(item.verification_status is VerificationStatus.UNVERIFIED for item in result.evidence_obtained))

    def test_fallo_parcial_no_borra_resultados_validos(self):
        assessment = assess()
        good = FakeResearchCapability("good", (ResearchCategory.DEMAND, ResearchCategory.MARKETPLACE, ResearchCategory.SUPPLIER, ResearchCategory.COSTS))
        bad = FakeResearchCapability("bad", (ResearchCategory.COMPETITION,), mode="timeout")
        plan = plan_for(assessment, (bad, good))
        result = execute_research_plan(plan=plan, assessment=assessment, capabilities=(bad, good), execution_context=CTX, generated_at=NOW)
        self.assertEqual(len(result.completed_tasks), 3)
        self.assertEqual(len(result.failed_tasks), 1)
        self.assertEqual(len(result.evidence_obtained), 3)

    def test_predecessor_fallido_bloquea_dependiente(self):
        assessment = assess()
        good = FakeResearchCapability("good", (ResearchCategory.DEMAND, ResearchCategory.SUPPLIER, ResearchCategory.COSTS), region_codes=("US",))
        bad = FakeResearchCapability("bad", (ResearchCategory.COMPETITION,), region_codes=("US",), mode="timeout")
        base = plan_for(assessment, (bad, good))
        competition = next(item for item in base.tasks if item.category is ResearchCategory.COMPETITION)
        demand = next(item for item in base.tasks if item.category is ResearchCategory.DEMAND)
        dependency = ResearchTaskDependency(competition.task_id, demand.task_id, "Demand se ejecuta después de validar el contexto competitivo.")
        plan = ResearchPlan(base.investigation_id, base.tasks, (dependency,), base.reusable_evidence, base.missing_context, base.warnings, base.created_at, base.plan_version, base.business_path_id)
        result = execute_research_plan(plan=plan, assessment=assessment, capabilities=(bad, good), execution_context=CTX, generated_at=NOW)
        self.assertIn(competition.task_id, result.failed_tasks)
        self.assertIn(demand.task_id, result.blocked_tasks)
        self.assertTrue(result.completed_tasks)

    def test_assessment_serializable_e_inmutable(self):
        result = self.execute()
        json.dumps(result.to_dict())
        with self.assertRaises(FrozenInstanceError):
            result.warnings = ()

    def test_coverage_no_es_porcentaje_agregado(self):
        payload = self.execute("partial").to_dict()
        self.assertIsInstance(payload["coverage"], list)
        self.assertNotIn("coverage_score", payload)
        self.assertNotIn("coverage_percentage", payload)

    def test_assessment_no_modifica_decision(self):
        payload = json.dumps(self.execute().to_dict()).lower()
        self.assertNotIn("decision", payload)
        self.assertNotIn("recommendation", payload)


class ArchitectureTests(unittest.TestCase):
    def test_production_no_contiene_integraciones_reales(self):
        root = Path(__file__).resolve().parents[1]
        text = "\n".join((root / path).read_text().lower() for path in ("application/research_models.py", "application/research_orchestration_service.py", "application/ports/research_capability.py"))
        for forbidden in ("sp-api", "jungle scout", "keepa", "google", "requests", "oauth", "openai", "asyncio", "threading"):
            self.assertNotIn(forbidden, text)

    def test_domain_permanece_independiente(self):
        root = Path(__file__).resolve().parents[1] / "domain"
        text = "\n".join(path.read_text().lower() for path in root.rglob("*.py"))
        for forbidden in ("from application", "import application", "streamlit", "requests", "sqlalchemy"):
            self.assertNotIn(forbidden, text)

    def test_no_se_modifican_entidades_historicas(self):
        assessment = assess()
        before = assessment.to_dict()
        plan = plan_for(assessment)
        execute_research_plan(plan=plan, assessment=assessment, capabilities=capabilities(), execution_context=CTX, generated_at=NOW)
        self.assertEqual(assessment.to_dict(), before)


if __name__ == "__main__":
    unittest.main()
