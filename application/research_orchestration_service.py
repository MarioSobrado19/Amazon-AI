"""Planificador y ejecutor síncrono del Research Orchestrator V1."""

from dataclasses import replace
from datetime import datetime

from application.research_models import (
    EvidenceAccess, EvidenceVisibility, ResearchCapabilityRequest,
    ResearchCapabilityResultStatus, ResearchCoverage, ResearchCoverageStatus,
    ResearchExecutionContext, ResearchPlan, ResearchPlanAssessment,
    ResearchPriority, ResearchTask, ResearchTaskDependency, ResearchTaskState,
)
from domain.contracts import ResearchAssessment
from domain.entities import EvidenceRecord
from domain.enums import EvidenceType, FreshnessStatus, ResearchCategory, VerificationStatus
from domain.exceptions import DomainValidationError


ORCHESTRATOR_VERSION = "research-orchestrator/1.0"


def _is_accessible(evidence, access_by_id, scope_id):
    access = access_by_id.get(evidence.evidence_id)
    if access is None:
        return False
    return access.visibility is EvidenceVisibility.PUBLIC_REUSABLE or access.owner_scope_id == scope_id


def _is_applicable(evidence, need, question, access_by_id, scope_id, conflicting_ids):
    access = access_by_id.get(evidence.evidence_id)
    return (
        evidence.evidence_id not in conflicting_ids
        and evidence.subject_type == need.subject_type
        and evidence.subject_id == need.subject_id
        and evidence.category is need.category
        and evidence.evidence_type is EvidenceType.DATA
        and evidence.evidence_type in need.required_evidence_types
        and evidence.verification_status is VerificationStatus.VERIFIED
        and evidence.freshness is FreshnessStatus.CURRENT
        and (question.region is None or evidence.region == question.region)
        and (question.marketplace_id is None or evidence.marketplace_id == question.marketplace_id)
        and (question.time_scope is None or (access is not None and access.time_scope == question.time_scope))
        and _is_accessible(evidence, access_by_id, scope_id)
    )


def validate_task_dag(tasks, dependencies):
    ids = {task.task_id for task in tasks}
    edges = set()
    outgoing = {task_id: set() for task_id in ids}
    indegree = {task_id: 0 for task_id in ids}
    for dependency in dependencies:
        if dependency.predecessor_task_id not in ids or dependency.dependent_task_id not in ids:
            raise DomainValidationError("La dependencia referencia una tarea inexistente.")
        edge = (dependency.predecessor_task_id, dependency.dependent_task_id)
        if edge in edges:
            raise DomainValidationError("La dependencia está duplicada.")
        edges.add(edge)
        outgoing[edge[0]].add(edge[1])
        indegree[edge[1]] += 1
    queue = sorted(key for key, degree in indegree.items() if degree == 0)
    visited = []
    while queue:
        current = queue.pop(0)
        visited.append(current)
        for dependent in sorted(outgoing[current]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                queue.append(dependent)
                queue.sort()
    if len(visited) != len(ids):
        raise DomainValidationError("Las dependencias de investigación contienen un ciclo.")
    return tuple(visited)


def parallelizable_groups(plan):
    """Devuelve capas topológicas; cada capa puede ejecutarse en paralelo."""
    remaining = {task.task_id for task in plan.tasks if task.state is not ResearchTaskState.SKIPPED_REUSED}
    predecessors = {task_id: set() for task_id in remaining}
    for dependency in plan.dependencies:
        if dependency.dependent_task_id in remaining and dependency.predecessor_task_id in remaining:
            predecessors[dependency.dependent_task_id].add(dependency.predecessor_task_id)
    groups = []
    resolved = set()
    while remaining:
        ready = tuple(sorted(task_id for task_id in remaining if predecessors[task_id] <= resolved))
        if not ready:
            raise DomainValidationError("El plan no es un DAG ejecutable.")
        groups.append(ready)
        resolved.update(ready)
        remaining.difference_update(ready)
    return tuple(groups)


def create_research_plan(*, assessment, capabilities, execution_context,
                         evidence_access=(), dependencies=(), created_at,
                         plan_version=ORCHESTRATOR_VERSION):
    if not isinstance(assessment, ResearchAssessment):
        raise DomainValidationError("assessment debe ser ResearchAssessment.")
    if not isinstance(execution_context, ResearchExecutionContext):
        raise DomainValidationError("execution_context debe ser válido.")
    capabilities = tuple(capabilities)
    access = tuple(evidence_access)
    if any(not isinstance(item, EvidenceAccess) for item in access):
        raise DomainValidationError("evidence_access contiene valores inválidos.")
    access_by_id = {item.evidence_id: item for item in access}
    if len(access_by_id) != len(access):
        raise DomainValidationError("evidence_access contiene duplicados.")
    needs = {need.need_id: need for need in assessment.needs}
    questions = {question.research_need_id: question for question in assessment.questions}
    conflicting_ids = {item for conflict in assessment.conflicts for item in conflict.evidence_ids}
    tasks = []
    reusable = {}
    warnings = []
    for need_id, need in sorted(needs.items()):
        question = questions.get(need_id)
        if question is None:
            warnings.append(f"La necesidad {need_id} no tiene ResearchQuestion asociada.")
            continue
        applicable = tuple(item for item in assessment.evidence if _is_applicable(item, need, question, access_by_id, execution_context.scope_id, conflicting_ids))
        capability = None
        for candidate in capabilities:
            request = ResearchCapabilityRequest("planning-probe", need.category, question.question, need.subject_type, need.subject_id, execution_context, question.region, question.marketplace_id, question.time_scope)
            if candidate.can_handle(request):
                capability = candidate
                break
        if applicable:
            reusable.update((item.evidence_id, item) for item in applicable)
            state = ResearchTaskState.SKIPPED_REUSED
            capability_id = capability.capability_id if capability else "not_required_reused"
            missing_context = ()
            blocking_reason = None
        elif capability is None:
            state = ResearchTaskState.BLOCKED
            capability_id = "unavailable"
            missing_context = ("capability compatible",)
            blocking_reason = "No existe una ResearchCapability compatible."
        else:
            state = ResearchTaskState.READY
            capability_id = capability.capability_id
            missing_context = ()
            blocking_reason = None
        priority = ResearchPriority.BLOCKING if need.blocking else (ResearchPriority.HIGH if need.importance.lower() == "high" else ResearchPriority.NORMAL)
        priority_reason = "La necesidad bloquea el siguiente paso." if need.blocking else f"Prioridad declarada por ResearchNeed: {need.importance}."
        tasks.append(ResearchTask(need.need_id, question.question_id, need.category, need.subject_type, need.subject_id, capability_id, state, priority, priority_reason, reusable_evidence_ids=tuple(item.evidence_id for item in applicable), missing_context=missing_context, blocking_reason=blocking_reason, region=question.region, marketplace_id=question.marketplace_id, time_scope=question.time_scope, created_at=created_at))
    dependencies = tuple(dependencies)
    validate_task_dag(tasks, dependencies)
    dependent_ids = {item.dependent_task_id for item in dependencies}
    tasks = tuple(replace(task, dependencies=tuple(item.predecessor_task_id for item in dependencies if item.dependent_task_id == task.task_id), state=ResearchTaskState.BLOCKED if task.task_id in dependent_ids and task.state is ResearchTaskState.READY else task.state, blocking_reason="Esperando tareas predecesoras." if task.task_id in dependent_ids and task.state is ResearchTaskState.READY else task.blocking_reason) for task in tasks)
    return ResearchPlan(assessment.investigation.investigation_id, tasks, dependencies, tuple(reusable.values()), tuple(sorted({item for task in tasks for item in task.missing_context})), tuple(warnings), created_at, plan_version, assessment.investigation.business_path_id)


def _question_for_task(task, assessment):
    return next((item for item in assessment.questions if item.question_id == task.research_question_id), None)


def execute_research_plan(*, plan, assessment, capabilities, execution_context, generated_at):
    if not isinstance(plan, ResearchPlan) or not isinstance(assessment, ResearchAssessment):
        raise DomainValidationError("plan y assessment deben ser válidos.")
    capability_by_id = {item.capability_id: item for item in capabilities}
    results = {}
    completed = set()
    partial = set()
    no_data = set()
    failed = set()
    blocked = set()
    reused = {task.task_id for task in plan.tasks if task.state is ResearchTaskState.SKIPPED_REUSED}
    obtained = list(plan.reusable_evidence)
    failures = []
    warnings = list(plan.warnings)
    missing = set(plan.missing_context)
    for group in parallelizable_groups(plan):
        for task_id in group:
            task = next(item for item in plan.tasks if item.task_id == task_id)
            predecessors = {item.predecessor_task_id for item in plan.dependencies if item.dependent_task_id == task_id}
            if any(item in failed or item in blocked for item in predecessors):
                blocked.add(task_id)
                missing.add(f"Dependencia no completada para {task.category.value}.")
                continue
            capability = capability_by_id.get(task.capability_required)
            question = _question_for_task(task, assessment)
            if capability is None or question is None:
                blocked.add(task_id)
                missing.add(f"No hay capability/contexto para {task.category.value}.")
                continue
            request = ResearchCapabilityRequest(task.task_id, task.category, question.question, task.subject_type, task.subject_id, execution_context, task.region, task.marketplace_id, task.time_scope, task.reusable_evidence_ids)
            if not capability.can_handle(request):
                blocked.add(task_id)
                missing.add(f"Capability incompatible para {task.category.value}.")
                continue
            result = capability.execute(request)
            results[task_id] = result
            obtained.extend(result.evidence)
            warnings.extend(result.warnings)
            missing.update(result.missing_information)
            if result.status is ResearchCapabilityResultStatus.SUCCESS:
                completed.add(task_id)
            elif result.status is ResearchCapabilityResultStatus.PARTIAL:
                partial.add(task_id)
            elif result.status is ResearchCapabilityResultStatus.NO_DATA:
                no_data.add(task_id)
                missing.add(f"La capability no obtuvo evidencia suficiente para {task.category.value}.")
            else:
                failed.add(task_id)
                failures.append(result.failure)
    pending = {task.task_id for task in plan.tasks} - completed - partial - no_data - failed - blocked - reused
    coverage = []
    categories = sorted({task.category for task in plan.tasks}, key=lambda item: item.value)
    for category in categories:
        category_tasks = {task.task_id for task in plan.tasks if task.category is category}
        evidence_ids = tuple(item.evidence_id for item in obtained if item.category is category)
        if category_tasks & failed or category_tasks & blocked:
            status, explanation = ResearchCoverageStatus.MISSING, "La categoría conserva un fallo o bloqueo; no es evidencia comercial negativa."
        elif category_tasks & (partial | no_data):
            status, explanation = ResearchCoverageStatus.PARTIAL, "La capability produjo evidencia parcial o no obtuvo datos suficientes."
        elif any(item.category is category and item.freshness is FreshnessStatus.EXPIRED for item in obtained) and not any(item.category is category and item.freshness is FreshnessStatus.CURRENT for item in obtained):
            status, explanation = ResearchCoverageStatus.STALE, "Solo existe evidencia expirada; permanece visible y requiere actualización."
        elif category_tasks <= completed | reused:
            status, explanation = ResearchCoverageStatus.COVERED, "La categoría tiene resultado completado o evidencia reutilizada aplicable."
        else:
            status, explanation = ResearchCoverageStatus.MISSING, "La categoría continúa pendiente."
        coverage.append(ResearchCoverage(category, status, explanation, evidence_ids))
    return ResearchPlanAssessment(plan, tuple(completed), tuple(partial), tuple(no_data), tuple(failed), tuple(blocked), tuple(reused), tuple(pending), tuple(obtained), tuple(missing), tuple(item for item in failures if item is not None), tuple(warnings), tuple(coverage), generated_at)
