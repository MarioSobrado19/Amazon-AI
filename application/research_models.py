"""Contratos inmutables para planificar y ejecutar investigación.

Estos tipos describen coordinación; no contienen investigación, reglas
comerciales, fórmulas financieras ni recomendaciones.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from uuid import UUID, uuid5

from domain.entities import EvidenceRecord
from domain.entities._marketplace_validation import (
    aware_datetime, optional_text, required_text, text_tuple,
)
from domain.enums import ResearchCategory
from domain.exceptions import DomainValidationError
from domain.value_objects import FrozenMapping, Region
from domain.value_objects.sensitive_data import contains_sensitive_key, contains_sensitive_reference


_TASK_NAMESPACE = UUID("7e5d7e03-c13a-4dab-bfe9-6e0e15da1c9f")
_PLAN_NAMESPACE = UUID("158a6974-0f22-42dc-bdb2-8086725b3f38")


class ResearchTaskState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    BLOCKED = "blocked"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED_REUSED = "skipped_reused"


class ResearchPriority(str, Enum):
    BLOCKING = "blocking"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class ResearchCapabilityResultStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    NO_DATA = "no_data"
    FAILED = "failed"


class EvidenceVisibility(str, Enum):
    PRIVATE = "private"
    PROJECT_SCOPED = "project_scoped"
    PUBLIC_REUSABLE = "public_reusable"


class ResearchCoverageStatus(str, Enum):
    COVERED = "covered"
    PARTIAL = "partial"
    MISSING = "missing"
    STALE = "stale"
    CONFLICTED = "conflicted"


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class EvidenceAccess:
    evidence_id: str
    visibility: EvidenceVisibility
    owner_scope_id: str | None = None
    time_scope: str | None = None
    applicable_question_ids: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "evidence_id", required_text(self.evidence_id, "evidence_id"))
        if not isinstance(self.visibility, EvidenceVisibility):
            raise DomainValidationError("visibility debe ser válida.")
        object.__setattr__(self, "owner_scope_id", optional_text(self.owner_scope_id, "owner_scope_id"))
        object.__setattr__(self, "time_scope", optional_text(self.time_scope, "time_scope"))
        object.__setattr__(self, "applicable_question_ids", tuple(sorted(set(text_tuple(self.applicable_question_ids, "applicable_question_ids")))))
        if self.visibility is not EvidenceVisibility.PUBLIC_REUSABLE and not self.owner_scope_id:
            raise DomainValidationError("La evidencia no pública requiere owner_scope_id.")

    def to_dict(self):
        return {"evidence_id": self.evidence_id, "visibility": self.visibility.value, "owner_scope_id": self.owner_scope_id, "time_scope": self.time_scope, "applicable_question_ids": list(self.applicable_question_ids)}


@dataclass(frozen=True, slots=True)
class ResearchExecutionContext:
    scope_id: str
    correlation_id: str
    requested_at: datetime
    region: Region | None = None
    authorization_available: bool = False

    def __post_init__(self):
        object.__setattr__(self, "scope_id", required_text(self.scope_id, "scope_id"))
        object.__setattr__(self, "correlation_id", required_text(self.correlation_id, "correlation_id"))
        object.__setattr__(self, "requested_at", aware_datetime(self.requested_at, "requested_at"))
        if self.region is not None and not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser Region.")
        if not isinstance(self.authorization_available, bool):
            raise DomainValidationError("authorization_available debe ser booleano.")

    def to_dict(self):
        return {"scope_id": self.scope_id, "correlation_id": self.correlation_id, "requested_at": self.requested_at.isoformat(), "region": self.region.to_dict() if self.region else None, "authorization_available": self.authorization_available}


@dataclass(frozen=True, slots=True)
class ResearchTaskDependency:
    predecessor_task_id: str
    dependent_task_id: str
    reason: str

    def __post_init__(self):
        for field in ("predecessor_task_id", "dependent_task_id", "reason"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if self.predecessor_task_id == self.dependent_task_id:
            raise DomainValidationError("Una tarea no puede depender de sí misma.")

    def to_dict(self):
        return {"predecessor_task_id": self.predecessor_task_id, "dependent_task_id": self.dependent_task_id, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class ResearchTask:
    research_need_id: str
    research_question_id: str
    category: ResearchCategory
    subject_type: str
    subject_id: str
    capability_required: str
    state: ResearchTaskState
    priority: ResearchPriority
    priority_reason: str
    dependencies: tuple[str, ...] = ()
    reusable_evidence_ids: tuple[str, ...] = ()
    missing_context: tuple[str, ...] = ()
    blocking_reason: str | None = None
    region: Region | None = None
    marketplace_id: str | None = None
    time_scope: str | None = None
    created_at: datetime | None = None
    semantic_version: str = "1"
    task_id: str | None = None

    def __post_init__(self):
        for field in ("research_need_id", "research_question_id", "subject_type", "subject_id", "capability_required", "priority_reason", "semantic_version"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if not isinstance(self.category, ResearchCategory):
            raise DomainValidationError("category debe ser ResearchCategory.")
        if not isinstance(self.state, ResearchTaskState) or not isinstance(self.priority, ResearchPriority):
            raise DomainValidationError("state y priority deben ser válidos.")
        for field in ("dependencies", "reusable_evidence_ids", "missing_context"):
            object.__setattr__(self, field, tuple(sorted(set(text_tuple(getattr(self, field), field)))))
        object.__setattr__(self, "blocking_reason", optional_text(self.blocking_reason, "blocking_reason"))
        object.__setattr__(self, "marketplace_id", optional_text(self.marketplace_id, "marketplace_id"))
        object.__setattr__(self, "time_scope", optional_text(self.time_scope, "time_scope"))
        if self.region is not None and not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser Region.")
        if self.created_at is not None:
            object.__setattr__(self, "created_at", aware_datetime(self.created_at, "created_at"))
        semantic = _canonical({"need": self.research_need_id, "question": self.research_question_id, "category": self.category.value, "subject": [self.subject_type, self.subject_id], "region": self.region.to_dict() if self.region else None, "marketplace": self.marketplace_id, "time_scope": self.time_scope, "version": self.semantic_version})
        expected = str(uuid5(_TASK_NAMESPACE, semantic))
        if self.task_id is not None and self.task_id != expected:
            raise DomainValidationError("task_id no coincide con la tarea semántica.")
        object.__setattr__(self, "task_id", expected)

    def to_dict(self):
        return {"task_id": self.task_id, "research_need_id": self.research_need_id, "research_question_id": self.research_question_id, "category": self.category.value, "subject_type": self.subject_type, "subject_id": self.subject_id, "region": self.region.to_dict() if self.region else None, "marketplace_id": self.marketplace_id, "time_scope": self.time_scope, "capability_required": self.capability_required, "state": self.state.value, "priority": self.priority.value, "priority_reason": self.priority_reason, "dependencies": list(self.dependencies), "reusable_evidence_ids": list(self.reusable_evidence_ids), "missing_context": list(self.missing_context), "blocking_reason": self.blocking_reason, "created_at": self.created_at.isoformat() if self.created_at else None, "semantic_version": self.semantic_version}


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    investigation_id: str
    tasks: tuple[ResearchTask, ...]
    dependencies: tuple[ResearchTaskDependency, ...]
    reusable_evidence: tuple[EvidenceRecord, ...]
    missing_context: tuple[str, ...]
    warnings: tuple[str, ...]
    created_at: datetime
    plan_version: str
    business_path_id: str | None = None
    plan_id: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "investigation_id", required_text(self.investigation_id, "investigation_id"))
        tasks = tuple(sorted(tuple(self.tasks), key=lambda item: item.task_id))
        if any(not isinstance(item, ResearchTask) for item in tasks) or len({x.task_id for x in tasks}) != len(tasks):
            raise DomainValidationError("tasks contiene tareas inválidas o duplicadas.")
        object.__setattr__(self, "tasks", tasks)
        dependencies = tuple(sorted(tuple(self.dependencies), key=lambda x: (x.predecessor_task_id, x.dependent_task_id)))
        if any(not isinstance(item, ResearchTaskDependency) for item in dependencies) or len(set(dependencies)) != len(dependencies):
            raise DomainValidationError("dependencies contiene valores inválidos o duplicados.")
        object.__setattr__(self, "dependencies", dependencies)
        evidence = tuple(sorted(tuple(self.reusable_evidence), key=lambda item: item.evidence_id))
        if any(not isinstance(item, EvidenceRecord) for item in evidence):
            raise DomainValidationError("reusable_evidence contiene valores inválidos.")
        object.__setattr__(self, "reusable_evidence", evidence)
        for field in ("missing_context", "warnings"):
            object.__setattr__(self, field, tuple(sorted(set(text_tuple(getattr(self, field), field)))))
        object.__setattr__(self, "created_at", aware_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "plan_version", required_text(self.plan_version, "plan_version"))
        object.__setattr__(self, "business_path_id", optional_text(self.business_path_id, "business_path_id"))
        semantic = _canonical({"investigation": self.investigation_id, "business_path": self.business_path_id, "tasks": [x.task_id for x in tasks], "dependencies": [[x.predecessor_task_id, x.dependent_task_id, x.reason] for x in dependencies], "version": self.plan_version})
        expected = str(uuid5(_PLAN_NAMESPACE, semantic))
        if self.plan_id is not None and self.plan_id != expected:
            raise DomainValidationError("plan_id no coincide con el trabajo semántico.")
        object.__setattr__(self, "plan_id", expected)

    def to_dict(self):
        return {"plan_id": self.plan_id, "investigation_id": self.investigation_id, "business_path_id": self.business_path_id, "tasks": [x.to_dict() for x in self.tasks], "dependencies": [x.to_dict() for x in self.dependencies], "reusable_evidence": [x.to_dict() for x in self.reusable_evidence], "missing_context": list(self.missing_context), "warnings": list(self.warnings), "created_at": self.created_at.isoformat(), "plan_version": self.plan_version}


@dataclass(frozen=True, slots=True)
class ResearchCapabilityRequest:
    task_id: str
    category: ResearchCategory
    question: str
    subject_type: str
    subject_id: str
    execution_context: ResearchExecutionContext
    region: Region | None = None
    marketplace_id: str | None = None
    time_scope: str | None = None
    known_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for field in ("task_id", "question", "subject_type", "subject_id"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if not isinstance(self.category, ResearchCategory) or not isinstance(self.execution_context, ResearchExecutionContext):
            raise DomainValidationError("category o execution_context inválido.")
        if self.region is not None and not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser Region.")
        for field in ("marketplace_id", "time_scope"):
            object.__setattr__(self, field, optional_text(getattr(self, field), field))
        object.__setattr__(self, "known_evidence_ids", tuple(sorted(set(text_tuple(self.known_evidence_ids, "known_evidence_ids")))))

    def to_dict(self):
        return {"task_id": self.task_id, "category": self.category.value, "question": self.question, "subject_type": self.subject_type, "subject_id": self.subject_id, "region": self.region.to_dict() if self.region else None, "marketplace_id": self.marketplace_id, "time_scope": self.time_scope, "known_evidence_ids": list(self.known_evidence_ids), "execution_context": self.execution_context.to_dict()}


@dataclass(frozen=True, slots=True)
class ResearchFailure:
    code: str
    message: str
    retryable: bool
    capability_id: str
    occurred_at: datetime
    safe_context: FrozenMapping = FrozenMapping()

    def __post_init__(self):
        for field in ("code", "message", "capability_id"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if contains_sensitive_reference(self.message):
            raise DomainValidationError("message no puede contener credenciales o secretos.")
        if not isinstance(self.retryable, bool):
            raise DomainValidationError("retryable debe ser booleano.")
        object.__setattr__(self, "occurred_at", aware_datetime(self.occurred_at, "occurred_at"))
        context = self.safe_context if isinstance(self.safe_context, FrozenMapping) else FrozenMapping.from_mapping(self.safe_context)
        if contains_sensitive_key(context):
            raise DomainValidationError("safe_context no puede contener secretos o PII sensible.")
        object.__setattr__(self, "safe_context", context)

    def to_dict(self):
        return {"code": self.code, "message": self.message, "retryable": self.retryable, "capability_id": self.capability_id, "occurred_at": self.occurred_at.isoformat(), "safe_context": self.safe_context.to_dict()}


@dataclass(frozen=True, slots=True)
class ResearchCapabilityResult:
    task_id: str
    status: ResearchCapabilityResultStatus
    capability_id: str
    completed_at: datetime
    evidence: tuple[EvidenceRecord, ...] = ()
    missing_information: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    failure: ResearchFailure | None = None
    capability_version: str = "1"

    def __post_init__(self):
        for field in ("task_id", "capability_id", "capability_version"):
            object.__setattr__(self, field, required_text(getattr(self, field), field))
        if not isinstance(self.status, ResearchCapabilityResultStatus):
            raise DomainValidationError("status debe ser válido.")
        object.__setattr__(self, "completed_at", aware_datetime(self.completed_at, "completed_at"))
        evidence = tuple(self.evidence)
        if any(not isinstance(item, EvidenceRecord) for item in evidence):
            raise DomainValidationError("evidence contiene valores inválidos.")
        object.__setattr__(self, "evidence", evidence)
        for field in ("missing_information", "warnings"):
            object.__setattr__(self, field, tuple(sorted(set(text_tuple(getattr(self, field), field)))))
        if self.failure is not None and not isinstance(self.failure, ResearchFailure):
            raise DomainValidationError("failure debe ser ResearchFailure.")
        if self.status is ResearchCapabilityResultStatus.FAILED and self.failure is None:
            raise DomainValidationError("failed requiere failure.")
        if self.status is not ResearchCapabilityResultStatus.FAILED and self.failure is not None:
            raise DomainValidationError("Solo failed puede contener failure.")

    def to_dict(self):
        return {"task_id": self.task_id, "status": self.status.value, "capability_id": self.capability_id, "completed_at": self.completed_at.isoformat(), "evidence": [x.to_dict() for x in self.evidence], "missing_information": list(self.missing_information), "warnings": list(self.warnings), "failure": self.failure.to_dict() if self.failure else None, "capability_version": self.capability_version}


@dataclass(frozen=True, slots=True)
class ResearchCoverage:
    category: ResearchCategory
    status: ResearchCoverageStatus
    explanation: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.category, ResearchCategory) or not isinstance(self.status, ResearchCoverageStatus):
            raise DomainValidationError("category o status inválido.")
        object.__setattr__(self, "explanation", required_text(self.explanation, "explanation"))
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(text_tuple(self.evidence_ids, "evidence_ids")))))

    def to_dict(self):
        return {"category": self.category.value, "status": self.status.value, "explanation": self.explanation, "evidence_ids": list(self.evidence_ids)}


@dataclass(frozen=True, slots=True)
class ResearchPlanAssessment:
    plan: ResearchPlan
    completed_tasks: tuple[str, ...]
    partial_tasks: tuple[str, ...]
    no_data_tasks: tuple[str, ...]
    failed_tasks: tuple[str, ...]
    blocked_tasks: tuple[str, ...]
    reused_tasks: tuple[str, ...]
    pending_tasks: tuple[str, ...]
    evidence_obtained: tuple[EvidenceRecord, ...]
    missing_information: tuple[str, ...]
    failures: tuple[ResearchFailure, ...]
    warnings: tuple[str, ...]
    coverage: tuple[ResearchCoverage, ...]
    generated_at: datetime

    def __post_init__(self):
        if not isinstance(self.plan, ResearchPlan):
            raise DomainValidationError("plan debe ser ResearchPlan.")
        for field in ("completed_tasks", "partial_tasks", "no_data_tasks", "failed_tasks", "blocked_tasks", "reused_tasks", "pending_tasks", "missing_information", "warnings"):
            object.__setattr__(self, field, tuple(sorted(set(text_tuple(getattr(self, field), field)))))
        evidence = tuple(self.evidence_obtained)
        failures = tuple(self.failures)
        coverage = tuple(self.coverage)
        if any(not isinstance(x, EvidenceRecord) for x in evidence) or any(not isinstance(x, ResearchFailure) for x in failures) or any(not isinstance(x, ResearchCoverage) for x in coverage):
            raise DomainValidationError("Assessment contiene valores inválidos.")
        object.__setattr__(self, "evidence_obtained", evidence)
        object.__setattr__(self, "failures", failures)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "generated_at", aware_datetime(self.generated_at, "generated_at"))

    @property
    def status(self):
        if self.failed_tasks or self.partial_tasks or self.no_data_tasks or self.blocked_tasks or self.pending_tasks:
            return "partial"
        return "completed"

    def to_dict(self):
        return {"plan": self.plan.to_dict(), "status": self.status, "completed_tasks": list(self.completed_tasks), "partial_tasks": list(self.partial_tasks), "no_data_tasks": list(self.no_data_tasks), "failed_tasks": list(self.failed_tasks), "blocked_tasks": list(self.blocked_tasks), "reused_tasks": list(self.reused_tasks), "pending_tasks": list(self.pending_tasks), "evidence_obtained": [x.to_dict() for x in self.evidence_obtained], "missing_information": list(self.missing_information), "failures": [x.to_dict() for x in self.failures], "warnings": list(self.warnings), "coverage": [x.to_dict() for x in self.coverage], "generated_at": self.generated_at.isoformat()}
