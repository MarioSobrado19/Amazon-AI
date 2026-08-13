"""Proyector neutral y sin persistencia para Opportunity Graph V1."""

from datetime import datetime, timezone

from domain.contracts import (
    CandidateBusinessPath,
    EvidenceRelation,
    OpportunityGraphSnapshot,
)
from domain.entities import (
    BusinessModel,
    BusinessPath,
    Marketplace,
    Objective,
    Opportunity,
    OpportunityScenario,
    Product,
    Recommendation,
    Result,
)
from domain.enums import (
    ConfidenceLevel,
    EvidenceRelationType,
    EvidenceType,
    FreshnessStatus,
    GraphNodeType,
)
from domain.exceptions import DomainValidationError
from domain.value_objects import DomainNodeReference


OPPORTUNITY_GRAPH_VERSION = "opportunity-graph/1.0"
PROJECTOR_VERSION = "opportunity-graph-projector/1.0"
_STRUCTURAL_AT = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _node(value):
    specs = (
        (Objective, GraphNodeType.OBJECTIVE, "objective_id", "description", None),
        (BusinessPath, GraphNodeType.BUSINESS_PATH, "business_path_id", None, "version"),
        (CandidateBusinessPath, GraphNodeType.CANDIDATE_BUSINESS_PATH, "candidate_path_id", "appearance_reason", "version"),
        (OpportunityScenario, GraphNodeType.OPPORTUNITY_SCENARIO, "scenario_id", None, None),
        (Opportunity, GraphNodeType.OPPORTUNITY, "opportunity_id", None, None),
        (Product, GraphNodeType.PRODUCT, "product_id", "name", None),
        (Marketplace, GraphNodeType.MARKETPLACE, "marketplace_id", "name", "version"),
        (BusinessModel, GraphNodeType.BUSINESS_MODEL, "business_model_id", "name", "version"),
        (Result, GraphNodeType.RESULT, "result_id", "name", "version"),
        (Recommendation, GraphNodeType.RECOMMENDATION, "recommendation_id", "message", "version"),
    )
    for kind, node_type, id_field, label_field, version_field in specs:
        if isinstance(value, kind):
            return DomainNodeReference(
                node_type=node_type,
                domain_id=getattr(value, id_field),
                label=getattr(value, label_field) if label_field else None,
                version=str(getattr(value, version_field)) if version_field and getattr(value, version_field) is not None else None,
            )
    raise DomainValidationError(f"Tipo no soportado por Opportunity Graph: {type(value).__name__}.")


def _relation(source, target, relation_type, *, evidence_type=EvidenceType.DATA,
              evidence_source="Oriva domain reference", confidence=ConfidenceLevel.HIGH,
              evaluated_at=_STRUCTURAL_AT, freshness=None, explanation, assumptions=(), limitations=(), version="1"):
    return EvidenceRelation(
        _node(source), _node(target), relation_type, evidence_type, evidence_source,
        confidence, evaluated_at, explanation, version, freshness, assumptions, limitations,
    )


def _unique(values, key):
    return tuple({key(value): value for value in values}.values())


def _snapshot_context(snapshots):
    """Selecciona trazabilidad declarada sin ocultar snapshots vencidos."""
    snapshots = tuple(snapshots)
    if not snapshots:
        return {}
    chosen = sorted(snapshots, key=lambda item: (item.effective_at, item.snapshot_id))[-1]
    return {
        "evidence_type": EvidenceType.DATA,
        "evidence_source": chosen.source,
        "confidence": chosen.confidence,
        "evaluated_at": chosen.effective_at,
        "freshness": chosen.freshness,
        "version": chosen.version,
        "limitations": (
            ("La condición externa utilizada está vencida.",)
            if chosen.freshness is FreshnessStatus.EXPIRED else ()
        ),
    }


def project_opportunity_graph(
    *,
    generated_at,
    objective=None,
    goal_context=None,
    candidate_paths=(),
    business_paths=(),
    opportunities=(),
    scenarios=(),
    products=(),
    marketplaces=(),
    business_models=(),
    results=(),
    recommendations=(),
):
    """Construye una proyección parcial exclusivamente desde objetos suministrados."""
    if not isinstance(generated_at, datetime) or generated_at.tzinfo is None:
        raise DomainValidationError("generated_at debe incluir zona horaria.")
    if objective is not None and not isinstance(objective, Objective):
        raise DomainValidationError("objective debe ser Objective.")

    candidates = tuple(candidate_paths)
    paths = tuple(business_paths)
    supplied_opportunities = tuple(opportunities)
    supplied_scenarios = tuple(scenarios)
    supplied_products = tuple(products)
    supplied_marketplaces = tuple(marketplaces)
    supplied_models = tuple(business_models)
    supplied_results = tuple(results)
    supplied_recommendations = tuple(recommendations)
    expected = (
        (candidates, CandidateBusinessPath, "candidate_paths"),
        (paths, BusinessPath, "business_paths"),
        (supplied_opportunities, Opportunity, "opportunities"),
        (supplied_scenarios, OpportunityScenario, "scenarios"),
        (supplied_products, Product, "products"),
        (supplied_marketplaces, Marketplace, "marketplaces"),
        (supplied_models, BusinessModel, "business_models"),
        (supplied_results, Result, "results"),
        (supplied_recommendations, Recommendation, "recommendations"),
    )
    for values, kind, field in expected:
        if any(not isinstance(item, kind) for item in values):
            raise DomainValidationError(f"{field} contiene objetos inválidos.")

    # Los objetos contenidos en escenarios/candidatos son conocimiento explícito,
    # no descubrimiento. Se añaden sin copiar ni mutar las entidades originales.
    scenarios_all = supplied_scenarios + tuple(item.scenario for item in candidates if item.scenario)
    opportunities_all = supplied_opportunities + tuple(item.opportunity for item in scenarios_all)
    products_all = supplied_products + tuple(item.product for item in opportunities_all)
    marketplaces_all = supplied_marketplaces + tuple(item.marketplace for item in scenarios_all) + tuple(item.marketplace for item in candidates if item.marketplace)
    models_all = supplied_models + tuple(item.business_model for item in scenarios_all) + tuple(item.business_model for item in candidates if item.business_model)
    results_all = supplied_results + tuple(item for opportunity in opportunities_all for item in opportunity.financial_context) + tuple(item for path in paths for item in path.available_evidence + path.assumptions) + tuple(item for candidate in candidates for item in candidate.available_evidence + candidate.assumptions)
    recommendations_all = supplied_recommendations

    scenarios_all = _unique(scenarios_all, lambda x: x.scenario_id)
    opportunities_all = _unique(opportunities_all, lambda x: x.opportunity_id)
    products_all = _unique(products_all, lambda x: x.product_id)
    marketplaces_all = _unique(marketplaces_all, lambda x: x.marketplace_id)
    models_all = _unique(models_all, lambda x: x.business_model_id)
    results_all = _unique(results_all, lambda x: x.result_id)
    recommendations_all = _unique(recommendations_all, lambda x: x.recommendation_id)

    objects = ((objective,) if objective else ()) + candidates + paths + scenarios_all + opportunities_all + products_all + marketplaces_all + models_all + results_all + recommendations_all
    if not objects:
        raise DomainValidationError("Se requiere al menos un objeto para proyectar el grafo.")
    nodes_by_id = {_node(item).node_id: _node(item) for item in objects}
    relations = []
    missing = set()
    warnings = set()

    if goal_context is not None and objective is not None and getattr(goal_context, "objective_id", None) != objective.objective_id:
        raise DomainValidationError("goal_context debe pertenecer al objective suministrado.")

    for candidate in candidates:
        if objective and candidate.objective_id == objective.objective_id:
            relations.append(_relation(objective, candidate, EvidenceRelationType.PURSUES, explanation="El objetivo origina esta hipótesis temporal."))
        elif objective is None:
            missing.add(f"objective:{candidate.objective_id}")
        if candidate.scenario:
            relations.append(_relation(candidate, candidate.scenario, EvidenceRelationType.USES_SCENARIO, explanation="El candidato referencia este escenario."))
        if candidate.marketplace:
            relations.append(_relation(candidate, candidate.marketplace, EvidenceRelationType.TARGETS_MARKETPLACE, explanation="El candidato considera este marketplace sin afirmar conveniencia.", **_snapshot_context(candidate.condition_snapshots)))
        if candidate.business_model:
            relations.append(_relation(candidate, candidate.business_model, EvidenceRelationType.CONSIDERS_BUSINESS_MODEL, explanation="El candidato considera este modelo sin elegirlo."))
        missing.update(candidate.missing_evidence)
        for snapshot in candidate.condition_snapshots:
            if snapshot.freshness is FreshnessStatus.EXPIRED:
                warnings.add(f"Evidencia vencida conservada: {snapshot.condition_type} ({snapshot.snapshot_id}).")

    scenario_by_id = {item.scenario_id: item for item in scenarios_all}
    marketplace_by_id = {item.marketplace_id: item for item in marketplaces_all}
    model_by_id = {item.business_model_id: item for item in models_all}
    for path in paths:
        if objective and path.objective_id == objective.objective_id:
            relations.append(_relation(objective, path, EvidenceRelationType.PURSUES, explanation="El objetivo origina esta ruta persistente."))
        elif objective is None:
            missing.add(f"objective:{path.objective_id}")
        for scenario_id in path.scenario_ids:
            if scenario_id in scenario_by_id:
                relations.append(_relation(path, scenario_by_id[scenario_id], EvidenceRelationType.USES_SCENARIO, explanation="La ruta referencia este escenario canónico."))
            else:
                missing.add(f"opportunity_scenario:{scenario_id}")
        for marketplace_id in path.marketplace_ids:
            if marketplace_id in marketplace_by_id:
                relations.append(_relation(path, marketplace_by_id[marketplace_id], EvidenceRelationType.TARGETS_MARKETPLACE, explanation="La ruta referencia este marketplace sin afirmar adecuación."))
            else:
                missing.add(f"marketplace:{marketplace_id}")
        for model_id in path.business_model_ids:
            if model_id in model_by_id:
                relations.append(_relation(path, model_by_id[model_id], EvidenceRelationType.CONSIDERS_BUSINESS_MODEL, explanation="La ruta considera este modelo; no constituye una elección."))
            else:
                missing.add(f"business_model:{model_id}")
        missing.update(path.missing_evidence)

    for scenario in scenarios_all:
        relations.append(_relation(scenario, scenario.opportunity, EvidenceRelationType.EVALUATES, evaluated_at=scenario.evaluated_at, explanation="El escenario evalúa esta oportunidad."))
        marketplace_trace = _snapshot_context(scenario.conditions)
        if not marketplace_trace:
            marketplace_trace = {"evaluated_at": scenario.evaluated_at}
        relations.append(_relation(scenario, scenario.marketplace, EvidenceRelationType.TARGETS_MARKETPLACE, explanation="El escenario incluye este marketplace como contexto.", **marketplace_trace))
        relations.append(_relation(scenario, scenario.business_model, EvidenceRelationType.CONSIDERS_BUSINESS_MODEL, evaluated_at=scenario.evaluated_at, explanation="El escenario incluye este modelo operativo."))
        for snapshot in scenario.conditions:
            if snapshot.freshness is FreshnessStatus.EXPIRED:
                warnings.add(f"Evidencia vencida conservada: {snapshot.condition_type} ({snapshot.snapshot_id}).")

    for opportunity in opportunities_all:
        relations.append(_relation(opportunity, opportunity.product, EvidenceRelationType.CONCERNS_PRODUCT, evaluated_at=opportunity.evaluated_at, explanation="La oportunidad referencia este producto."))

    result_targets = {}
    for opportunity in opportunities_all:
        for item in opportunity.financial_context:
            result_targets[item.result_id] = opportunity
    for path in paths:
        for item in path.available_evidence + path.assumptions:
            result_targets.setdefault(item.result_id, path)
    for candidate in candidates:
        for item in candidate.available_evidence + candidate.assumptions:
            result_targets.setdefault(item.result_id, candidate)
    fallback_target = paths[0] if paths else (candidates[0] if candidates else (opportunities_all[0] if opportunities_all else objective))
    for result in results_all:
        target = result_targets.get(result.result_id, fallback_target)
        if target is None:
            missing.add(f"target_for_result:{result.result_id}")
            continue
        relation_type = EvidenceRelationType.ESTIMATED_BY if result.evidence_type is EvidenceType.ESTIMATE else EvidenceRelationType.SUPPORTS
        relations.append(_relation(
            result, target, relation_type, evidence_type=result.evidence_type,
            evidence_source=result.source, confidence=result.confidence,
            evaluated_at=result.recorded_at,
            explanation=(
                f"{result.name} aporta evidencia al contexto de esta referencia "
                f"como {result.evidence_type.value}; no valida conveniencia ni causalidad."
            ),
            assumptions=(result.name,) if result.evidence_type is EvidenceType.ASSUMPTION else (),
            version=result.version or "sin_version",
        ))

    opportunity_by_id = {item.opportunity_id: item for item in opportunities_all}
    for recommendation in recommendations_all:
        if recommendation.opportunity_id and recommendation.opportunity_id in opportunity_by_id:
            relations.append(_relation(recommendation, opportunity_by_id[recommendation.opportunity_id], EvidenceRelationType.DERIVED_FROM, evidence_type=EvidenceType.ESTIMATE, evidence_source="Oriva Decision Engine", confidence=recommendation.confidence, evaluated_at=recommendation.created_at, explanation="La recomendación se deriva de esta oportunidad y conserva sus limitaciones.", limitations=recommendation.limitations, version=recommendation.version))
        elif recommendation.opportunity_id:
            missing.add(f"opportunity:{recommendation.opportunity_id}")

    relation_by_id = {item.relation_id: item for item in relations}
    if not relation_by_id and len(nodes_by_id) > 1:
        warnings.add("Los objetos suministrados no contienen una relación verificable entre sí.")
    if missing:
        warnings.add("El grafo es parcial; conserva información faltante explícita.")

    root_object = objective or (paths[0] if paths else (candidates[0] if candidates else objects[0]))
    return OpportunityGraphSnapshot(
        root_node=_node(root_object),
        nodes=tuple(nodes_by_id.values()),
        relations=tuple(relation_by_id.values()),
        missing_information=tuple(sorted(missing)),
        warnings=tuple(sorted(warnings)),
        generated_at=generated_at,
        graph_version=OPPORTUNITY_GRAPH_VERSION,
        projector_version=PROJECTOR_VERSION,
    )
