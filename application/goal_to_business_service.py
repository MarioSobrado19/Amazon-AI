import json
from uuid import UUID, uuid5

from domain.contracts import (
    BusinessModelComparisonResult,
    CandidateBusinessPath,
    GoalToBusinessRequest,
    GoalToBusinessResult,
    MarketplaceCatalogResult,
    PathAssessment,
    PathDimensionAssessment,
)
from domain.entities import BusinessModel, Marketplace, Opportunity, OpportunityScenario
from domain.enums import CandidatePathState, ConfidenceLevel, FreshnessStatus, RiskLevel
from domain.exceptions import DomainValidationError


GOAL_TO_BUSINESS_VERSION = "goal-to-business/1.0"
_PATH_NAMESPACE = UUID("d5241545-680b-43a6-8f10-b47ff5e7d74f")
_CONFIDENCE_RANK = {ConfidenceLevel.LOW: 0, ConfidenceLevel.MEDIUM: 1, ConfidenceLevel.HIGH: 2}
_DIMENSIONS = (
    "capital", "tiempo", "experiencia", "logistica", "almacenamiento",
    "riesgo", "restricciones", "preferencias", "compatibilidad_regional",
    "modelo_operativo", "evidencia_disponible",
)


def _unique(*groups):
    return tuple(dict.fromkeys(item for group in groups for item in group if item))


def _lowest(*values):
    values = tuple(value for value in values if value is not None)
    return min(values, key=lambda value: _CONFIDENCE_RANK[value]) if values else ConfidenceLevel.LOW


def _path_id(request, marketplace, model, opportunity, scenario):
    """UUID5 semántico; nunca depende de orden ni fecha de ejecución.

    El nombre combina objetivo, snapshot canónico sin captured_at, marketplace,
    modelo, oportunidad, escenario y versión del servicio. El namespace fijo es
    privado de Goal-to-Business V1. `generated_at` pertenece al resultado, no a
    la identidad de la hipótesis.
    """
    context = request.context.to_dict()
    context.pop("captured_at", None)
    identity = "|".join((
        request.objective.objective_id,
        json.dumps(context, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
        marketplace.marketplace_id if marketplace else "none",
        model.business_model_id if model else "none",
        opportunity.opportunity_id if opportunity else "none",
        scenario.scenario_id if scenario else "none",
        GOAL_TO_BUSINESS_VERSION,
    ))
    return str(uuid5(_PATH_NAMESPACE, identity))


def _assessment_for_model(comparison, model):
    if comparison is None or model is None:
        return None
    return next((item for item in comparison.assessments if item.business_model == model), None)


def _dimension_from_model(assessment, dimension):
    if assessment is None:
        return None
    aliases = {
        "capital": "capital", "tiempo": "tiempo", "experiencia": "experiencia",
        "logistica": "logistica", "almacenamiento": "almacenamiento",
        "riesgo": "riesgo", "restricciones": "restric", "preferencias": "prefer",
        "compatibilidad_regional": "region", "modelo_operativo": "operativ",
    }
    needle = aliases.get(dimension)
    return next((item for item in assessment.dimensions if needle in item.dimension.casefold()), None)


def _context_dimension(request, dimension, marketplace, model, opportunity, assessment):
    context = request.context
    model_dimension = _dimension_from_model(assessment, dimension)
    if model_dimension:
        return PathDimensionAssessment(
            dimension, model_dimension.evaluation, model_dimension.explanation,
            model_dimension.confidence, model_dimension.evidence,
            model_dimension.missing_data,
            assessment.requirements if model_dimension.evaluation == "incompatible" else (),
        )
    fields = {
        "capital": context.available_budget,
        "tiempo": context.available_time_hours_per_week,
        "experiencia": context.experience,
        "logistica": context.logistics_capacity,
        "almacenamiento": context.storage_space,
        "riesgo": context.risk_tolerance,
    }
    if dimension in fields:
        value = fields[dimension]
        if value is None:
            return PathDimensionAssessment(dimension, "desconocida", f"Falta información declarada sobre {dimension}.", ConfidenceLevel.LOW, missing_data=(f"context.{dimension}",))
        return PathDimensionAssessment(dimension, "declarada", f"Existe información declarada sobre {dimension}, pero no se infiere compatibilidad sin requisitos verificables.", ConfidenceLevel.MEDIUM, evidence=(f"context.{dimension}",))
    if dimension == "restricciones":
        items = tuple(item.explanation for item in context.constraints)
        return PathDimensionAssessment(dimension, "declarada" if items else "desconocida", "Se conservaron las restricciones declaradas." if items else "No se declararon restricciones; esto no significa que no existan.", ConfidenceLevel.MEDIUM if items else ConfidenceLevel.LOW, evidence=items, missing_data=() if items else ("context.constraints",), relevant_constraints=items)
    if dimension == "preferencias":
        items = tuple(item.explanation or item.preference_type for item in context.preferences)
        return PathDimensionAssessment(dimension, "orientativa" if items else "desconocida", "Las preferencias orientan la comparación y no invalidan el camino." if items else "No se declararon preferencias.", ConfidenceLevel.MEDIUM if items else ConfidenceLevel.LOW, evidence=items, missing_data=() if items else ("context.preferences",))
    if dimension == "compatibilidad_regional":
        if context.region is None or marketplace is None:
            return PathDimensionAssessment(dimension, "desconocida", "Falta región o marketplace para comprobar compatibilidad.", ConfidenceLevel.LOW, missing_data=("region_or_marketplace",))
        compatible = context.region.country_code == marketplace.region.country_code
        return PathDimensionAssessment(dimension, "compatible" if compatible else "incompatible", "La región declarada coincide con el marketplace." if compatible else "La región declarada no coincide con el marketplace.", ConfidenceLevel.HIGH, evidence=(context.region.country_code, marketplace.region.country_code), relevant_constraints=() if compatible else ("region_incompatible",))
    if dimension == "modelo_operativo":
        return PathDimensionAssessment(dimension, "identificado" if model else "desconocida", "El modelo operativo fue suministrado explícitamente." if model else "Falta un modelo operativo conocido.", model.confidence if model else ConfidenceLevel.LOW, evidence=(model.business_model_id,) if model else (), missing_data=() if model else ("business_model",))
    evidence = tuple(item.name for item in opportunity.financial_context) if opportunity else ()
    return PathDimensionAssessment(dimension, "parcial" if evidence else "desconocida", "Existe evidencia suministrada, pero no demuestra viabilidad comercial." if evidence else "Falta una oportunidad con evidencia verificable.", ConfidenceLevel.MEDIUM if evidence else ConfidenceLevel.LOW, evidence=evidence, missing_data=() if evidence else ("opportunity_evidence",))


def _hard_incompatibilities(request, marketplace, model, assessment):
    reasons = []
    if request.context.region and marketplace and request.context.region.country_code != marketplace.region.country_code:
        reasons.append("La región declarada no coincide con el marketplace.")
    if assessment and assessment.compatibility == "incompatible":
        reasons.extend(assessment.reasons or assessment.unfavorable_factors or ("El modelo fue declarado incompatible por Business Model Engine.",))
    restrictions = {value.casefold() for value in (model.restrictions if model else ())}
    for item in request.context.constraints:
        if item.severity is RiskLevel.HIGH and (item.constraint_type.casefold() in restrictions or item.explanation.casefold() in restrictions):
            reasons.append(item.explanation)
    return _unique(reasons)


def _build_path(request, catalog, comparison, marketplace, model, opportunity, scenario):
    assessment_source = _assessment_for_model(comparison, model)
    dimensions = tuple(_context_dimension(request, name, marketplace, model, opportunity, assessment_source) for name in _DIMENSIONS)
    hard = _hard_incompatibilities(request, marketplace, model, assessment_source)
    expired = bool(catalog and marketplace and any(s.marketplace == marketplace and s.freshness in (FreshnessStatus.EXPIRED, FreshnessStatus.UNKNOWN) for s in catalog.snapshots))
    snapshots = tuple(s for s in (catalog.snapshots if catalog else ()) if marketplace and s.marketplace == marketplace)
    missing = _unique(*(item.missing_data for item in dimensions), ("opportunity",) if opportunity is None else (), ("actualizar_condiciones",) if expired else ())
    if hard:
        state = CandidatePathState.INVALIDATED
    elif opportunity and marketplace and model:
        state = CandidatePathState.RESEARCHABLE
    elif opportunity:
        state = CandidatePathState.HYPOTHESIS
    else:
        state = CandidatePathState.INCOMPLETE
    confidence = _lowest(catalog.confidence if catalog else None, comparison.confidence if comparison else None, *(item.confidence for item in dimensions))
    if expired or not opportunity:
        confidence = ConfidenceLevel.LOW
    evidence = _unique(opportunity.financial_context if opportunity else (), scenario.costs if scenario else ())
    assumptions = scenario.assumptions if scenario else ()
    risks = _unique(hard, ("La evidencia externa está vencida o tiene vigencia desconocida.",) if expired else (), ("No se verificaron demanda, competencia, proveedor ni costos finales.",))
    return CandidateBusinessPath(
        _path_id(request, marketplace, model, opportunity, scenario), request.objective.objective_id,
        request.context, PathAssessment(dimensions, confidence, GOAL_TO_BUSINESS_VERSION), state, confidence,
        GOAL_TO_BUSINESS_VERSION, marketplace, model, scenario,
        tuple(model.requirements) if model else (), tuple(catalog.capabilities) if catalog else (),
        tuple(item.explanation for item in request.context.constraints),
        tuple(item.explanation or item.preference_type for item in request.context.preferences),
        tuple(evidence), snapshots, missing, tuple(assumptions), risks, hard,
        ("Actualizar condiciones externas antes de continuar.",) if expired else ("Investigar los datos faltantes antes de considerar una decisión.",),
        "Se construyó únicamente con candidatos suministrados explícitamente." if opportunity else "Estructura parcial: todavía no existe una oportunidad comercial suministrada.",
    )


def generar_caminos_candidatos(request, *, marketplace_catalog=None, business_model_comparison=None, opportunities=(), scenarios=(), generated_at=None):
    if not isinstance(request, GoalToBusinessRequest): raise DomainValidationError("request debe ser GoalToBusinessRequest.")
    if marketplace_catalog is not None and not isinstance(marketplace_catalog, MarketplaceCatalogResult): raise DomainValidationError("marketplace_catalog no es válido.")
    if business_model_comparison is not None and not isinstance(business_model_comparison, BusinessModelComparisonResult): raise DomainValidationError("business_model_comparison no es válido.")
    opportunities, scenarios = tuple(opportunities), tuple(scenarios)
    if any(not isinstance(x, Opportunity) for x in opportunities) or any(not isinstance(x, OpportunityScenario) for x in scenarios): raise DomainValidationError("Los candidatos suministrados no son válidos.")
    generated_at = generated_at or request.context.captured_at
    marketplaces = marketplace_catalog.marketplaces if marketplace_catalog else ()
    models = business_model_comparison.compatible_models if business_model_comparison else (marketplace_catalog.business_models if marketplace_catalog else ())
    seeds = []
    for scenario in scenarios: seeds.append((scenario.marketplace, scenario.business_model, scenario.opportunity, scenario))
    if not scenarios:
        for opportunity in opportunities:
            market = next((x for x in marketplaces if x.marketplace_id == opportunity.marketplace_id), None)
            if models: seeds.extend((market, model, opportunity, None) for model in models)
            else: seeds.append((market, None, opportunity, None))
    if not seeds and models:
        for model in models:
            market = next((x for x in marketplaces if model.marketplace_id in (None, x.marketplace_id)), None)
            seeds.append((market, model, None, None))
    if not seeds: seeds.append((marketplaces[0] if marketplaces else None, None, None, None))
    unique_seeds = []
    seen = set()
    for seed in seeds:
        key = tuple(
            item.scenario_id if isinstance(item, OpportunityScenario)
            else item.opportunity_id if isinstance(item, Opportunity)
            else item.business_model_id if isinstance(item, BusinessModel)
            else item.marketplace_id if isinstance(item, Marketplace)
            else None
            for item in seed
        )
        if key not in seen:
            seen.add(key)
            unique_seeds.append(seed)
    paths = tuple(_build_path(request, marketplace_catalog, business_model_comparison, *seed) for seed in unique_seeds)
    valid = tuple(x for x in paths if x.state is not CandidatePathState.INVALIDATED)
    invalid = tuple(x for x in paths if x.state is CandidatePathState.INVALIDATED)
    global_missing = _unique(*(x.missing_evidence for x in paths))
    warnings = ("No contamos todavía con oportunidades verificables; no se inventó una ruta comercial.",) if not opportunities and not scenarios else ()
    if marketplace_catalog and any(s.freshness in (FreshnessStatus.EXPIRED, FreshnessStatus.UNKNOWN) for s in marketplace_catalog.snapshots): warnings += ("Se conservó evidencia histórica que necesita actualización.",)
    questions = tuple(f"¿Cómo confirmarás {item}?" for item in global_missing[:5])
    return GoalToBusinessResult(valid, invalid, global_missing, warnings, questions, GOAL_TO_BUSINESS_VERSION, generated_at)
