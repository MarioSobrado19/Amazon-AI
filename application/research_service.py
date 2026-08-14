"""Orquestación determinista del estado de conocimiento de una ruta."""

from datetime import datetime
import json
from uuid import UUID, uuid5

from domain.contracts import EvidenceConflict, ResearchAssessment
from domain.entities import (
    BusinessPath, EvidenceRecord, Investigation, Opportunity,
    OpportunityScenario, ResearchFinding,
)
from domain.enums import (
    ConfidenceLevel, ConflictResolutionStatus, EvidenceType, FreshnessStatus,
    InvestigationStatus, ResearchCategory, ResearchQuestionStatus,
    VerificationStatus,
)
from domain.exceptions import DomainValidationError
from domain.value_objects import ResearchNeed, ResearchQuestion


RESEARCH_SERVICE_VERSION = "research-service/1.0"
_INVESTIGATION_NAMESPACE = UUID("4dfacfb9-6528-42f4-b5a5-8108a0c133b6")
_FINDING_NAMESPACE = UUID("116c7d15-91ef-4d65-acda-6cd49c881bc3")

_ALIASES = {
    "demand": ("demand", "demanda"),
    "competition": ("competition", "competencia"),
    "supplier": ("supplier", "proveedor"),
    "marketplace": ("marketplace", "mercado", "canal"),
    "costs": ("cost", "costo", "coste", "tarifa"),
    "restrictions": ("restriction", "restriccion", "restricción"),
    "logistics": ("logistic", "logística", "logistica", "envío", "envio"),
}
_QUESTIONS = {
    ResearchCategory.DEMAND: "¿Existe evidencia verificable de demanda para este sujeto en el marketplace, región y periodo relevantes?",
    ResearchCategory.COMPETITION: "¿Qué evidencia verificable describe la competencia relevante para este sujeto?",
    ResearchCategory.SUPPLIER: "¿Existe un proveedor verificable y cuáles son sus condiciones vigentes?",
    ResearchCategory.MARKETPLACE: "¿Qué condiciones vigentes del marketplace aplican a este sujeto?",
    ResearchCategory.COSTS: "¿Cuáles son los costos finales verificables y vigentes para este sujeto?",
    ResearchCategory.RESTRICTIONS: "¿Qué restricciones verificables y vigentes aplican a este sujeto?",
    ResearchCategory.LOGISTICS: "¿Qué condiciones logísticas verificables requiere este sujeto?",
}


def _category(text):
    normalized = text.lower()
    for key, aliases in _ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return ResearchCategory(key)
    return None


def _investigation_id(path):
    return str(uuid5(_INVESTIGATION_NAMESPACE, f"business_path:{path.business_path_id}"))


def _finding(investigation_id, evidence):
    canonical = json.dumps({"investigation": investigation_id, "evidence": evidence.evidence_id, "version": evidence.version}, sort_keys=True, separators=(",", ":"))
    identifier = str(uuid5(_FINDING_NAMESPACE, canonical))
    kind = EvidenceType.ASSUMPTION if evidence.evidence_type is EvidenceType.ASSUMPTION else EvidenceType.ESTIMATE
    return ResearchFinding(
        identifier, investigation_id,
        f"La investigación conserva una observación de {evidence.category.value}; su interpretación está limitada por la evidencia disponible.",
        (evidence.evidence_id,), kind, evidence.confidence,
        evidence.limitations or ("El hallazgo no demuestra viabilidad ni resultados comerciales.",),
        evidence.retrieved_at, evidence.version,
    )


def assess_business_path_research(*, business_path, evidence=(), assessed_at,
                                  previous_assessment=None, opportunity=None,
                                  scenario=None):
    if not isinstance(business_path, BusinessPath):
        raise DomainValidationError("business_path debe ser BusinessPath.")
    if not isinstance(assessed_at, datetime) or assessed_at.tzinfo is None:
        raise DomainValidationError("assessed_at debe incluir zona horaria.")
    if opportunity is not None and not isinstance(opportunity, Opportunity):
        raise DomainValidationError("opportunity debe ser Opportunity.")
    if scenario is not None and not isinstance(scenario, OpportunityScenario):
        raise DomainValidationError("scenario debe ser OpportunityScenario.")
    if scenario is not None and opportunity is not None and scenario.opportunity.opportunity_id != opportunity.opportunity_id:
        raise DomainValidationError("scenario y opportunity deben corresponder.")
    if scenario is not None and business_path.scenario_ids and scenario.scenario_id not in business_path.scenario_ids:
        raise DomainValidationError("scenario no pertenece al BusinessPath.")
    supplied = tuple(evidence)
    if any(not isinstance(item, EvidenceRecord) for item in supplied):
        raise DomainValidationError("evidence contiene registros inválidos.")
    if previous_assessment is not None and not isinstance(previous_assessment, ResearchAssessment):
        raise DomainValidationError("previous_assessment debe ser ResearchAssessment.")
    previous_evidence = previous_assessment.evidence if previous_assessment else ()
    evidence_by_id = {item.evidence_id: item for item in previous_evidence + supplied}
    records = tuple(sorted(evidence_by_id.values(), key=lambda x: (x.retrieved_at, x.evidence_id)))
    if any(item.subject_id != business_path.business_path_id for item in records):
        raise DomainValidationError("Toda evidencia debe pertenecer al BusinessPath analizado.")

    explicit_missing = tuple(business_path.missing_evidence)
    uncategorized_missing = tuple(
        text for text in explicit_missing if _category(text) is None
    )
    categories = []
    for text in explicit_missing:
        category = _category(text)
        if category and category not in categories:
            categories.append(category)
    grouped = {category: tuple(item for item in records if item.category is category) for category in ResearchCategory}
    needs = []
    questions = []
    for category in categories:
        items = grouped[category]
        verified_current = tuple(item for item in items if item.evidence_type is EvidenceType.DATA and item.verification_status is VerificationStatus.VERIFIED and item.freshness is FreshnessStatus.CURRENT)
        known = tuple(f"{item.evidence_type.value}:{item.evidence_id}" for item in items)
        reason = f"Falta resolver información de {category.value} para esta ruta."
        need = ResearchNeed("business_path", business_path.business_path_id, category, reason, "high", True, (EvidenceType.DATA,), known, (category.value,))
        if verified_current:
            status = ResearchQuestionStatus.VERIFIED
        elif items and all(item.freshness is FreshnessStatus.EXPIRED for item in items):
            status = ResearchQuestionStatus.STALE
        elif items:
            status = ResearchQuestionStatus.PARTIAL
        else:
            status = ResearchQuestionStatus.PENDING
        questions.append(ResearchQuestion(need.need_id, _QUESTIONS[category], "business_path", business_path.business_path_id, (EvidenceType.DATA,), status, region=business_path.context.region, marketplace_id=business_path.marketplace_ids[0] if business_path.marketplace_ids else None))
        if not verified_current:
            needs.append(need)

    findings = tuple(_finding(_investigation_id(business_path), item) for item in records)
    conflicts = []
    for category in ResearchCategory:
        items = grouped[category]
        active_items = tuple(
            item for item in items if item.freshness is not FreshnessStatus.EXPIRED
        )
        distinct = {
            json.dumps(item.value.to_dict(), sort_keys=True, ensure_ascii=False)
            for item in active_items
        }
        if len(active_items) > 1 and len(distinct) > 1:
            conflicts.append(EvidenceConflict("business_path", business_path.business_path_id, category, tuple(item.evidence_id for item in active_items), f"Existen observaciones activas incompatibles sobre {category.value}; no se seleccionó una ganadora.", ConflictResolutionStatus.OPEN, assessed_at))

    verified = tuple(f"{item.category.value}:{item.evidence_id}" for item in records if item.evidence_type is EvidenceType.DATA and item.verification_status is VerificationStatus.VERIFIED and item.freshness is FreshnessStatus.CURRENT)
    stale = tuple(f"{item.category.value}:{item.evidence_id}" for item in records if item.freshness is FreshnessStatus.EXPIRED)
    unverified = tuple(f"{item.category.value}:{item.evidence_id}" for item in records if item.verification_status is not VerificationStatus.VERIFIED or item.evidence_type is not EvidenceType.DATA)
    confidence = ConfidenceLevel.HIGH if not needs and not conflicts and verified else (ConfidenceLevel.MEDIUM if records and not conflicts else ConfidenceLevel.LOW)
    if stale and confidence is ConfidenceLevel.HIGH:
        confidence = ConfidenceLevel.MEDIUM
    status = InvestigationStatus.VERIFIED if confidence is ConfidenceLevel.HIGH else (InvestigationStatus.STALE if stale and not any(item.freshness is FreshnessStatus.CURRENT for item in records) else (InvestigationStatus.PARTIAL if records else InvestigationStatus.PENDING))
    prior = previous_assessment.investigation if previous_assessment else None
    version = prior.version + 1 if prior else 1
    created_at = prior.created_at if prior else assessed_at
    unresolved = tuple(sorted(set(
        tuple(need.category.value for need in needs) + uncategorized_missing
    )))
    investigation = Investigation(_investigation_id(business_path), "business_path", business_path.business_path_id, status, tuple(item.question_id for item in questions), tuple(item.finding_id for item in findings), unresolved, created_at, assessed_at, version, business_path_id=business_path.business_path_id, opportunity_id=opportunity.opportunity_id if opportunity else None, scenario_id=scenario.scenario_id if scenario else None, supersedes_version=prior.version if prior else None)
    limitations = ["La evaluación describe conocimiento disponible y no recomienda comprar, invertir o ejecutar."]
    if conflicts:
        limitations.append("Hay evidencia contradictoria sin resolver.")
    next_steps = tuple(f"Investigar: {item.question}" for item in questions if item.status is not ResearchQuestionStatus.VERIFIED)
    return ResearchAssessment(investigation, tuple(needs), tuple(questions), records, findings, tuple(conflicts), verified, unverified, stale, unresolved, tuple(need.category.value for need in needs if need.blocking), confidence, tuple(limitations), next_steps, assessed_at, RESEARCH_SERVICE_VERSION)
