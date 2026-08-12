from dataclasses import replace
import json
from uuid import UUID, uuid5

from domain.contracts import CandidateBusinessPath
from domain.contracts.business_path_promotion_result import BusinessPathPromotionResult
from domain.entities import BusinessPath, Result
from domain.entities._validation import required_text
from domain.enums import (
    BusinessPathState,
    CandidatePathState,
    EvidenceType,
    PathPromotionAction,
)
from domain.exceptions import DomainValidationError


BUSINESS_PATH_PROMOTION_VERSION = "business-path-promotion/1.0"
_BUSINESS_PATH_NAMESPACE = UUID("7fa95761-017e-4a93-8c1d-11853c9e870b")
_TRANSITIONS = {
    BusinessPathState.SAVED: {
        BusinessPathState.INVESTIGATING,
        BusinessPathState.PAUSED,
        BusinessPathState.INVALIDATED,
        BusinessPathState.CLOSED,
    },
    BusinessPathState.INVESTIGATING: {
        BusinessPathState.PAUSED,
        BusinessPathState.INVALIDATED,
        BusinessPathState.CLOSED,
    },
    BusinessPathState.PAUSED: {
        BusinessPathState.INVESTIGATING,
        BusinessPathState.INVALIDATED,
        BusinessPathState.CLOSED,
    },
    BusinessPathState.INVALIDATED: {BusinessPathState.CLOSED},
    BusinessPathState.CLOSED: set(),
}


def _persistent_id(candidate):
    """ID estable por estructura comercial, nunca por contexto del usuario.

    La identidad usa objetivo, escenarios, marketplaces y modelos operativos.
    El contexto y el ID técnico del candidato se excluyen. Si todavía no existe
    ninguna referencia comercial, todos los candidatos del mismo objetivo
    representan la misma ruta parcial hasta que una versión posterior incorpore
    escenario, marketplace o modelo y establezca otra identidad material.
    """
    scenario_ids = (candidate.scenario.scenario_id,) if candidate.scenario else ()
    marketplace_ids = (candidate.marketplace.marketplace_id,) if candidate.marketplace else ()
    model_ids = (candidate.business_model.business_model_id,) if candidate.business_model else ()
    identity = {
        "objective_id": candidate.objective_id,
        "scenario_ids": scenario_ids,
        "marketplace_ids": marketplace_ids,
        "business_model_ids": model_ids,
    }
    canonical = json.dumps(identity, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return str(uuid5(_BUSINESS_PATH_NAMESPACE, canonical))


def promote_candidate_business_path(
    candidate,
    *,
    action,
    actor_id,
    promoted_at,
    existing_paths=(),
    reason=None,
):
    if not isinstance(candidate, CandidateBusinessPath):
        raise DomainValidationError("candidate debe ser CandidateBusinessPath.")
    if not isinstance(action, PathPromotionAction):
        raise DomainValidationError("Se requiere una acción humana explícita.")
    actor_id = required_text(actor_id, "actor_id")
    reason = required_text(reason or (
        "El usuario guardó el camino para revisarlo."
        if action is PathPromotionAction.SAVE
        else "El usuario decidió investigar formalmente el camino."
    ), "reason")
    if candidate.state is CandidatePathState.INVALIDATED:
        raise DomainValidationError("Un candidato invalidado no puede promocionarse.")
    existing_paths = tuple(existing_paths)
    if any(not isinstance(item, BusinessPath) for item in existing_paths):
        raise DomainValidationError("existing_paths contiene rutas inválidas.")
    path_id = _persistent_id(candidate)
    if any(item.business_path_id == path_id or item.source_candidate_id == candidate.candidate_path_id for item in existing_paths):
        raise DomainValidationError("El candidato ya fue promovido; no se creó un duplicado.")
    state = BusinessPathState.SAVED if action is PathPromotionAction.SAVE else BusinessPathState.INVESTIGATING
    scenario_ids = (candidate.scenario.scenario_id,) if candidate.scenario else ()
    marketplace_ids = (candidate.marketplace.marketplace_id,) if candidate.marketplace else ()
    model_ids = (candidate.business_model.business_model_id,) if candidate.business_model else ()
    snapshot_ids = tuple(item.snapshot_id for item in candidate.condition_snapshots)
    path = BusinessPath(
        path_id, candidate.objective_id, candidate.candidate_path_id, candidate.context,
        scenario_ids, marketplace_ids, model_ids, snapshot_ids, state,
        candidate.available_evidence, candidate.missing_evidence,
        candidate.relevant_constraints, candidate.risks, candidate.assumptions,
        candidate.next_steps, promoted_at, promoted_at, 1, actor_id, reason,
    )
    warnings = (
        ("El camino conserva datos faltantes y no está listo para ejecución.",)
        if candidate.missing_evidence else ()
    )
    return BusinessPathPromotionResult(
        path, candidate, action, actor_id, promoted_at,
        BUSINESS_PATH_PROMOTION_VERSION, warnings,
    )


def transition_business_path(
    path,
    new_state,
    *,
    actor_id,
    reason,
    evaluated_at,
    supporting_evidence=(),
):
    if not isinstance(path, BusinessPath):
        raise DomainValidationError("path debe ser BusinessPath.")
    if not isinstance(new_state, BusinessPathState):
        raise DomainValidationError("new_state debe ser válido.")
    if new_state not in _TRANSITIONS[path.state]:
        raise DomainValidationError(f"Transición no permitida: {path.state.value} → {new_state.value}.")
    actor_id = required_text(actor_id, "actor_id")
    reason = required_text(reason, "reason")
    evidence = tuple(supporting_evidence)
    if any(not isinstance(item, Result) for item in evidence):
        raise DomainValidationError("supporting_evidence contiene Result inválidos.")
    if new_state is BusinessPathState.INVALIDATED:
        verified = any(item.evidence_type is EvidenceType.DATA for item in evidence)
        if not verified:
            raise DomainValidationError(
                "Invalidar requiere evidencia verificable que contradiga el camino."
            )
    return replace(
        path,
        state=new_state,
        available_evidence=path.available_evidence + evidence,
        last_evaluated_at=evaluated_at,
        version=path.version + 1,
        retained_by=actor_id,
        state_change_reason=reason,
        supersedes_version=path.version,
    )


def reevaluate_business_path(
    path,
    *,
    context,
    actor_id,
    reason,
    evaluated_at,
    additional_evidence=(),
    missing_evidence=None,
    constraints=None,
    risks=None,
    additional_assumptions=(),
    additional_condition_snapshot_ids=(),
    next_steps=None,
):
    """Crea una versión evaluada nueva sin cambiar identidad ni versión previa."""
    from domain.value_objects import GoalContextSnapshot

    if not isinstance(path, BusinessPath):
        raise DomainValidationError("path debe ser BusinessPath.")
    if not isinstance(context, GoalContextSnapshot):
        raise DomainValidationError("context debe ser GoalContextSnapshot.")
    if context.objective_id != path.objective_id:
        raise DomainValidationError("context debe pertenecer al objetivo de la ruta.")
    actor_id = required_text(actor_id, "actor_id")
    reason = required_text(reason, "reason")

    new_evidence = tuple(additional_evidence)
    new_assumptions = tuple(additional_assumptions)
    if any(not isinstance(item, Result) for item in new_evidence + new_assumptions):
        raise DomainValidationError("La reevaluación contiene Result inválidos.")
    evidence_by_id = {item.result_id: item for item in path.available_evidence}
    evidence_by_id.update({item.result_id: item for item in new_evidence})
    assumptions_by_id = {item.result_id: item for item in path.assumptions}
    assumptions_by_id.update({item.result_id: item for item in new_assumptions})
    snapshot_ids = tuple(
        dict.fromkeys(
            path.condition_snapshot_ids + tuple(additional_condition_snapshot_ids)
        )
    )

    return replace(
        path,
        context=context,
        available_evidence=tuple(evidence_by_id.values()),
        condition_snapshot_ids=snapshot_ids,
        missing_evidence=(path.missing_evidence if missing_evidence is None else tuple(missing_evidence)),
        constraints=(path.constraints if constraints is None else tuple(constraints)),
        risks=(path.risks if risks is None else tuple(risks)),
        assumptions=tuple(assumptions_by_id.values()),
        next_steps=(path.next_steps if next_steps is None else tuple(next_steps)),
        last_evaluated_at=evaluated_at,
        version=path.version + 1,
        retained_by=actor_id,
        state_change_reason=reason,
        supersedes_version=path.version,
    )
