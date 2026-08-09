from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from domain.contracts import (
    BusinessModelAssessment,
    BusinessModelComparisonResult,
    BusinessModelContext,
    BusinessModelDimensionEvaluation,
    MarketplaceCatalogResult,
)
from domain.entities import BusinessModel
from domain.entities._identity import new_internal_id
from domain.enums import ConfidenceLevel, OperationalLoad, RiskLevel
from domain.exceptions import DomainValidationError


BUSINESS_MODEL_ENGINE_VERSION = "business-model-engine/1.0"
_LEVEL_RANK = {
    "ninguna": 0,
    "ninguno": 0,
    "bajo": 1,
    "baja": 1,
    "limitado": 1,
    "medio": 2,
    "media": 2,
    "moderado": 2,
    "alto": 3,
    "alta": 3,
    "amplio": 3,
}
_EXPERIENCE_RANK = {"principiante": 1, "intermedio": 2, "avanzado": 3}
_RISK_RANK = {RiskLevel.LOW.value: 1, RiskLevel.MEDIUM.value: 2, RiskLevel.HIGH.value: 3}
_CONFIDENCE_RANK = {
    ConfidenceLevel.LOW: 0,
    ConfidenceLevel.MEDIUM: 1,
    ConfidenceLevel.HIGH: 2,
}


def _unique_text(*groups):
    return tuple(dict.fromkeys(item for group in groups for item in group if item))


def _profile(model):
    return model.comparison_profile.to_dict()


def _profile_text(profile, field):
    value = profile.get(field)
    return value.strip().lower() if isinstance(value, str) and value.strip() else None


def _profile_decimal(profile, field):
    value = profile.get(field)
    if value is None or isinstance(value, bool):
        return None
    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return value if value.is_finite() and value >= 0 else None


def _dimension(
    name,
    evaluation,
    explanation,
    *,
    confidence=ConfidenceLevel.HIGH,
    evidence=(),
    missing=(),
):
    return BusinessModelDimensionEvaluation(
        dimension=name,
        evaluation=evaluation,
        explanation=explanation,
        confidence=confidence,
        evidence=tuple(evidence),
        missing_data=tuple(missing),
    )


def _base_evidence(model, field):
    return _unique_text(
        (f"business_model_id:{model.business_model_id}",),
        (f"model_version:{model.version}",),
        (f"source:{model.source}",) if model.source else (),
        (f"comparison_profile:{field}",),
    )


def _capital_dimension(model, context, beginner):
    profile = _profile(model)
    required = _profile_decimal(profile, "minimum_budget_amount")
    currency = _profile_text(profile, "budget_currency")
    if required is None or currency is None:
        return _dimension(
            "capital_requerido",
            "desconocida",
            "No existe una estimación normalizada de capital mínimo.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "minimum_budget_amount"),
            missing=("model.minimum_budget",),
        )
    if context.budget is None:
        return _dimension(
            "capital_requerido",
            "desconocida",
            "Falta tu presupuesto para compararlo con el capital estimado del modelo.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "minimum_budget_amount"),
            missing=("context.budget",),
        )
    if context.budget.currency.casefold() != currency.casefold():
        return _dimension(
            "capital_requerido",
            "desconocida",
            "Las monedas no coinciden y no se aplicó una conversión implícita.",
            confidence=ConfidenceLevel.LOW,
            evidence=_unique_text(
                _base_evidence(model, "minimum_budget_amount"),
                (f"context.budget_currency:{context.budget.currency}",),
            ),
            missing=("currency_conversion",),
        )
    if context.budget.amount < required:
        explanation = (
            f"Tu presupuesto declarado es menor que el mínimo estimado de {required} {currency}."
            if not beginner
            else "El presupuesto indicado no alcanza el mínimo estimado."
        )
        return _dimension(
            "capital_requerido",
            "incompatible",
            explanation,
            evidence=_unique_text(
                _base_evidence(model, "minimum_budget_amount"),
                (f"context.budget:{context.budget.amount} {context.budget.currency}",),
            ),
        )
    return _dimension(
        "capital_requerido",
        "favorable",
        (
            f"El presupuesto cubre el mínimo estimado de {required} {currency}."
            if not beginner
            else "El presupuesto cubre el mínimo estimado."
        ),
        evidence=_unique_text(
            _base_evidence(model, "minimum_budget_amount"),
            (f"context.budget:{context.budget.amount} {context.budget.currency}",),
        ),
    )


def _time_dimension(model, context, beginner):
    required = _profile_decimal(_profile(model), "minimum_time_hours")
    if required is None:
        return _dimension(
            "tiempo_requerido",
            "desconocida",
            "No existe una estimación normalizada del tiempo mínimo.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "minimum_time_hours"),
            missing=("model.minimum_time_hours",),
        )
    if context.available_time_hours is None:
        return _dimension(
            "tiempo_requerido",
            "desconocida",
            "Faltan las horas disponibles por semana.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "minimum_time_hours"),
            missing=("context.available_time_hours",),
        )
    if context.available_time_hours < required:
        return _dimension(
            "tiempo_requerido",
            "incompatible",
            (
                f"Dispones de {context.available_time_hours} horas y el modelo estima al menos {required}."
                if not beginner
                else "El tiempo disponible es menor que el mínimo estimado."
            ),
            evidence=_unique_text(
                _base_evidence(model, "minimum_time_hours"),
                (f"context.available_time_hours:{context.available_time_hours}",),
            ),
        )
    return _dimension(
        "tiempo_requerido",
        "favorable",
        (
            f"Las {context.available_time_hours} horas disponibles cubren el mínimo estimado de {required}."
            if not beginner
            else "El tiempo disponible cubre el mínimo estimado."
        ),
        evidence=_unique_text(
            _base_evidence(model, "minimum_time_hours"),
            (f"context.available_time_hours:{context.available_time_hours}",),
        ),
    )


def _level_dimension(
    *,
    model,
    dimension,
    profile_field,
    context_field,
    context_value,
    beginner,
    hard_constraint,
):
    required = _profile_text(_profile(model), profile_field)
    if required not in _LEVEL_RANK:
        return _dimension(
            dimension,
            "desconocida",
            f"Falta el nivel normalizado de {dimension.replace('_', ' ')}.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, profile_field),
            missing=(f"model.{profile_field}",),
        )
    if context_value is None:
        return _dimension(
            dimension,
            "desconocida",
            f"Falta declarar {context_field.replace('_', ' ')}.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, profile_field),
            missing=(f"context.{context_field}",),
        )
    actual = _LEVEL_RANK[context_value]
    needed = _LEVEL_RANK[required]
    evidence = _unique_text(
        _base_evidence(model, profile_field),
        (f"context.{context_field}:{context_value}",),
    )
    if actual < needed:
        return _dimension(
            dimension,
            "incompatible" if hard_constraint else "desfavorable",
            (
                f"El modelo requiere nivel {required} y declaraste {context_value}."
                if not beginner
                else "La capacidad declarada es menor que la requerida."
            ),
            evidence=evidence,
        )
    return _dimension(
        dimension,
        "favorable",
        (
            f"El nivel declarado ({context_value}) cubre el requerido ({required})."
            if not beginner
            else "La capacidad declarada cubre lo requerido."
        ),
        evidence=evidence,
    )


def _complexity_dimension(model, context, beginner):
    required = _profile_text(_profile(model), "complexity_level")
    if required not in _LEVEL_RANK:
        return _dimension(
            "complejidad",
            "desconocida",
            "Falta el nivel normalizado de complejidad.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "complexity_level"),
            missing=("model.complexity_level",),
        )
    if context.experience is None:
        return _dimension(
            "complejidad",
            "desconocida",
            "Falta el nivel de experiencia para interpretar la complejidad.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "complexity_level"),
            missing=("context.experience",),
        )
    needed = _LEVEL_RANK[required]
    actual = _EXPERIENCE_RANK[context.experience]
    evaluation = "favorable" if actual >= needed else "desfavorable"
    return _dimension(
        "complejidad",
        evaluation,
        (
            f"La complejidad {required} se comparó con experiencia {context.experience}."
            if not beginner
            else (
                "La complejidad parece manejable para tu experiencia."
                if evaluation == "favorable"
                else "Este modelo puede ser complejo para empezar."
            )
        ),
        evidence=_unique_text(
            _base_evidence(model, "complexity_level"),
            (f"context.experience:{context.experience}",),
        ),
    )


def _control_dimension(model, context, beginner):
    level = _profile_text(_profile(model), "control_level")
    preference = context.operational_control_preference
    if level not in _LEVEL_RANK:
        return _dimension(
            "control_del_usuario",
            "desconocida",
            "Falta el nivel normalizado de control operativo.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "control_level"),
            missing=("model.control_level",),
        )
    if preference is None:
        return _dimension(
            "control_del_usuario",
            "desconocida",
            "Falta indicar cuánto control operativo prefieres.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "control_level"),
            missing=("context.operational_control_preference",),
        )
    distance = abs(_LEVEL_RANK[level] - _LEVEL_RANK[preference])
    evaluation = "favorable" if distance == 0 else "neutral" if distance == 1 else "desfavorable"
    return _dimension(
        "control_del_usuario",
        evaluation,
        (
            f"El modelo ofrece control {level}; tu preferencia es {preference}."
            if not beginner
            else "Se comparó el control del modelo con el control que prefieres."
        ),
        evidence=_unique_text(
            _base_evidence(model, "control_level"),
            (f"context.operational_control_preference:{preference}",),
        ),
    )


def _experience_dimension(model, context, beginner):
    recommended = (
        model.recommended_experience.casefold()
        if model.recommended_experience
        else _profile_text(_profile(model), "recommended_experience")
    )
    if recommended not in _EXPERIENCE_RANK:
        return _dimension(
            "experiencia_recomendada",
            "desconocida",
            "Falta una experiencia recomendada normalizada.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "recommended_experience"),
            missing=("model.recommended_experience",),
        )
    if context.experience is None:
        return _dimension(
            "experiencia_recomendada",
            "desconocida",
            "Falta tu experiencia para realizar esta comparación.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "recommended_experience"),
            missing=("context.experience",),
        )
    evaluation = (
        "favorable"
        if _EXPERIENCE_RANK[context.experience] >= _EXPERIENCE_RANK[recommended]
        else "desfavorable"
    )
    return _dimension(
        "experiencia_recomendada",
        evaluation,
        (
            f"El modelo recomienda experiencia {recommended}; declaraste {context.experience}."
            if not beginner
            else (
                "Tu experiencia cubre la recomendada."
                if evaluation == "favorable"
                else "Conviene aprender algunos conceptos antes de avanzar."
            )
        ),
        evidence=_unique_text(
            _base_evidence(model, "recommended_experience"),
            (f"context.experience:{context.experience}",),
        ),
    )


def _risk_dimension(model, context, beginner):
    level = _profile_text(_profile(model), "risk_level")
    if level not in _RISK_RANK:
        return _dimension(
            "riesgos",
            "desconocida",
            "Falta un nivel de riesgo normalizado; los riesgos textuales siguen visibles.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "risk_level"),
            missing=("model.risk_level",),
        )
    if context.risk_tolerance is None:
        return _dimension(
            "riesgos",
            "desconocida",
            "Falta tu tolerancia al riesgo.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "risk_level"),
            missing=("context.risk_tolerance",),
        )
    tolerance = context.risk_tolerance.value
    evaluation = "favorable" if _RISK_RANK[tolerance] >= _RISK_RANK[level] else "desfavorable"
    return _dimension(
        "riesgos",
        evaluation,
        (
            f"El riesgo declarado del modelo es {level}; tu tolerancia es {tolerance}."
            if not beginner
            else "Se comparó el riesgo del modelo con el que aceptas."
        ),
        evidence=_unique_text(
            _base_evidence(model, "risk_level"),
            (f"context.risk_tolerance:{tolerance}",),
        ),
    )


def _region_dimension(model, context, beginner):
    if context.region is None:
        return _dimension(
            "compatibilidad_regional",
            "desconocida",
            "Falta la región del usuario.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "region"),
            missing=("context.region",),
        )
    compatible = model.region == context.region
    return _dimension(
        "compatibilidad_regional",
        "favorable" if compatible else "incompatible",
        (
            "La región coincide con la disponibilidad del modelo."
            if compatible
            else "El modelo no está disponible en la región declarada."
        ),
        evidence=_unique_text(
            _base_evidence(model, "region"),
            (f"context.region:{context.region.country_code}:{context.region.area}",),
        ),
    )


def _operational_load_dimension(model):
    return _dimension(
        "carga_operativa",
        "neutral",
        f"La carga operativa declarada es {model.operational_load.value}.",
        confidence=model.confidence,
        evidence=_unique_text(
            _base_evidence(model, "operational_load"),
            (f"operational_load:{model.operational_load.value}",),
        ),
    )


def _scalability_dimension(model, context):
    level = _profile_text(_profile(model), "scalability_level")
    if level not in _LEVEL_RANK:
        return _dimension(
            "escalabilidad",
            "desconocida",
            "Falta un nivel de escalabilidad normalizado.",
            confidence=ConfidenceLevel.LOW,
            evidence=_base_evidence(model, "scalability_level"),
            missing=("model.scalability_level",),
        )
    objective = context.objective.casefold() if context.objective else None
    evaluation = "favorable" if objective == "escalar" and _LEVEL_RANK[level] >= 2 else "neutral"
    return _dimension(
        "escalabilidad",
        evaluation,
        f"La escalabilidad declarada es {level}; objetivo: {objective or 'no declarado'}.",
        confidence=model.confidence if objective else ConfidenceLevel.MEDIUM,
        evidence=_unique_text(
            _base_evidence(model, "scalability_level"),
            (f"context.objective:{objective}",) if objective else (),
        ),
        missing=() if objective else ("context.objective",),
    )


def _restriction_dimension(model, context):
    declared_incompatibilities = _profile(model).get(
        "incompatible_user_restrictions", []
    )
    normalized_incompatibilities = (
        {
            str(item).strip().casefold()
            for item in declared_incompatibilities
            if str(item).strip()
        }
        if isinstance(declared_incompatibilities, list)
        else set()
    )
    matched = tuple(
        item
        for item in context.declared_restrictions
        if item.casefold() in normalized_incompatibilities
    )
    if matched:
        return _dimension(
            "restricciones",
            "incompatible",
            "Una restricción declarada por el usuario es incompatible con este modelo: "
            + ", ".join(matched)
            + ".",
            evidence=_unique_text(
                _base_evidence(model, "incompatible_user_restrictions"),
                tuple(f"context.restriction:{item}" for item in matched),
            ),
        )

    missing = ()
    evaluation = "neutral"
    if model.restrictions or context.declared_restrictions:
        evaluation = "desconocida"
        missing = ("restriction_compatibility_verification",)
    return _dimension(
        "restricciones",
        evaluation,
        (
            "Las restricciones se mantienen visibles y requieren verificación humana; no se compararon por palabras."
            if missing
            else "No hay restricciones declaradas para contrastar."
        ),
        confidence=ConfidenceLevel.LOW if missing else model.confidence,
        evidence=_unique_text(
            _base_evidence(model, "incompatible_user_restrictions"),
            tuple(f"model.restriction:{item}" for item in model.restrictions),
            tuple(f"context.restriction:{item}" for item in context.declared_restrictions),
        ),
        missing=missing,
    )


def _evaluate_model(model, catalog, context, assessed_at):
    beginner = context.is_beginner
    dimensions = (
        _capital_dimension(model, context, beginner),
        _operational_load_dimension(model),
        _time_dimension(model, context, beginner),
        _complexity_dimension(model, context, beginner),
        _level_dimension(
            model=model,
            dimension="logistica",
            profile_field="logistics_requirement",
            context_field="logistics_capacity",
            context_value=context.logistics_capacity,
            beginner=beginner,
            hard_constraint=True,
        ),
        _level_dimension(
            model=model,
            dimension="almacenamiento",
            profile_field="storage_requirement",
            context_field="storage_space",
            context_value=context.storage_space,
            beginner=beginner,
            hard_constraint=True,
        ),
        _scalability_dimension(model, context),
        _control_dimension(model, context, beginner),
        _experience_dimension(model, context, beginner),
        _risk_dimension(model, context, beginner),
        _restriction_dimension(model, context),
        _region_dimension(model, context, beginner),
    )
    explicit_incompatibility = any(item.evaluation == "incompatible" for item in dimensions)
    known_context = 10 - len(context.missing_fields())
    if explicit_incompatibility:
        compatibility = "incompatible"
    elif known_context < 3:
        compatibility = "indeterminado"
    elif any(item.evaluation in {"desfavorable", "desconocida"} for item in dimensions):
        compatibility = "compatible_con_condiciones"
    else:
        compatibility = "compatible"

    if catalog.confidence is ConfidenceLevel.LOW or len(context.missing_fields()) >= 7:
        confidence = ConfidenceLevel.LOW
    elif catalog.confidence is ConfidenceLevel.MEDIUM or len(context.missing_fields()) >= 3:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.HIGH
    if any(item.confidence is ConfidenceLevel.LOW for item in dimensions):
        confidence = min(
            (confidence, ConfidenceLevel.MEDIUM),
            key=lambda item: _CONFIDENCE_RANK[item],
        )

    favorable = tuple(
        item.explanation for item in dimensions if item.evaluation == "favorable"
    )
    unfavorable = tuple(
        item.explanation
        for item in dimensions
        if item.evaluation in {"desfavorable", "incompatible"}
    )
    missing = _unique_text(
        context.missing_fields(),
        catalog.missing_data,
        *(item.missing_data for item in dimensions),
    )
    changes = []
    change_by_dimension = {
        "capital_requerido": "Aumentar el presupuesto o validar un requisito de capital menor.",
        "tiempo_requerido": "Disponer de más tiempo o reducir la carga estimada.",
        "logistica": "Ampliar la capacidad logística o verificar un requisito menor.",
        "almacenamiento": "Conseguir más espacio o verificar una necesidad menor.",
        "complejidad": "Adquirir experiencia o apoyo operativo adicional.",
        "control_del_usuario": "Cambiar la preferencia de control o revisar otra alternativa.",
        "experiencia_recomendada": "Completar preparación educativa antes de avanzar.",
        "riesgos": "Reducir la exposición o revisar la tolerancia al riesgo.",
        "compatibilidad_regional": "Seleccionar una región donde el modelo esté disponible.",
    }
    for item in dimensions:
        if item.evaluation in {"desfavorable", "incompatible"}:
            changes.append(change_by_dimension.get(item.dimension, item.explanation))

    profile_topics = _profile(model).get("educational_topics", [])
    if not isinstance(profile_topics, list):
        profile_topics = []
    educational_topics = _unique_text(
        tuple(str(item) for item in profile_topics if str(item).strip()),
        ("responsabilidades del modelo", "requisitos y restricciones"),
    )
    favorable_context = []
    unfavorable_context = []
    for field_name, value, label in (
        ("suitable_objectives", context.objective, "objetivo"),
        ("suitable_stages", context.business_stage, "etapa del negocio"),
    ):
        declared = _profile(model).get(field_name, [])
        normalized = (
            tuple(str(item).casefold() for item in declared)
            if isinstance(declared, list)
            else ()
        )
        if value and normalized:
            message = f"El {label} declarado ({value})"
            if value.casefold() in normalized:
                favorable_context.append(f"{message} coincide con el perfil del modelo.")
            else:
                unfavorable_context.append(
                    f"{message} no figura entre los contextos declarados del modelo."
                )
    return BusinessModelAssessment(
        assessment_id=new_internal_id(),
        scenario=None,
        compatibility=compatibility,
        confidence=confidence,
        version=BUSINESS_MODEL_ENGINE_VERSION,
        assessed_at=assessed_at,
        favorable_factors=favorable,
        unfavorable_factors=unfavorable,
        missing_information=missing,
        rules_applied=tuple(item.dimension for item in dimensions),
        business_model=model,
        dimensions=dimensions,
        risks=model.risks,
        requirements=model.requirements,
        seller_responsibilities=model.seller_responsibilities,
        marketplace_responsibilities=model.marketplace_responsibilities,
        favorable_context=tuple(favorable_context),
        unfavorable_context=tuple(unfavorable_context),
        reasons=tuple(item.explanation for item in dimensions),
        change_conditions=_unique_text(tuple(changes)),
        educational_topics=educational_topics,
        simplified_for_beginner=beginner,
    )


def _select_consideration(assessments, context):
    candidates = tuple(
        item
        for item in assessments
        if item.compatibility in {"compatible", "compatible_con_condiciones"}
    )
    if not candidates:
        return None, None, ()
    if len(candidates) == 1:
        model = candidates[0].business_model
        return (
            model,
            "Este modelo merece mayor consideración porque es la única alternativa sin incompatibilidades explícitas; la decisión sigue siendo del usuario.",
            (),
        )
    preference = context.operational_control_preference
    if preference is not None:
        exact = tuple(
            item
            for item in candidates
            if _profile_text(_profile(item.business_model), "control_level") == preference
        )
        if len(exact) == 1:
            model = exact[0].business_model
            alternatives = tuple(
                item.business_model for item in candidates if item is not exact[0]
            )
            return (
                model,
                f"Este modelo parece ajustarse mejor a la preferencia declarada de control {preference}; no es una elección automática.",
                alternatives,
            )
    objective = context.objective.casefold() if context.objective else None
    if objective:
        matching = tuple(
            item
            for item in candidates
            if objective in tuple(
                str(value).casefold()
                for value in _profile(item.business_model).get("suitable_objectives", [])
            )
        )
        if len(matching) == 1:
            model = matching[0].business_model
            alternatives = tuple(
                item.business_model for item in candidates if item is not matching[0]
            )
            return (
                model,
                f"Este modelo merece mayor consideración por su relación declarada con el objetivo {objective}; conviene revisar las compensaciones.",
                alternatives,
            )
    return (
        None,
        "Hay varias alternativas razonables y el contexto actual no ofrece un diferenciador explícito.",
        tuple(item.business_model for item in candidates),
    )


def comparar_modelos_operativos(
    catalog: MarketplaceCatalogResult,
    context: BusinessModelContext | None = None,
    *,
    assessed_at: datetime | None = None,
):
    """Compara dimensiones declaradas; no calcula ni oculta un score agregado."""

    if not isinstance(catalog, MarketplaceCatalogResult):
        raise DomainValidationError("catalog debe ser MarketplaceCatalogResult válido.")
    context = context or BusinessModelContext()
    if not isinstance(context, BusinessModelContext):
        raise DomainValidationError("context debe ser BusinessModelContext válido.")
    assessed_at = assessed_at or datetime.now(timezone.utc)
    if assessed_at.tzinfo is None or assessed_at.utcoffset() is None:
        raise DomainValidationError("assessed_at debe incluir zona horaria.")

    assessments = tuple(
        _evaluate_model(model, catalog, context, assessed_at)
        for model in catalog.business_models
    )
    compatible = tuple(
        item.business_model
        for item in assessments
        if item.compatibility in {"compatible", "compatible_con_condiciones"}
    )
    incompatible = tuple(
        item.business_model for item in assessments if item.compatibility == "incompatible"
    )
    consideration, reason, alternatives = _select_consideration(assessments, context)
    missing = _unique_text(
        context.missing_fields(),
        catalog.missing_data,
        *(item.missing_information for item in assessments),
    )
    if not assessments:
        missing = _unique_text(missing, ("business_models",))
        confidence = ConfidenceLevel.LOW
    elif any(item.confidence is ConfidenceLevel.LOW for item in assessments):
        confidence = ConfidenceLevel.LOW
    elif any(item.confidence is ConfidenceLevel.MEDIUM for item in assessments):
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.HIGH
    question = (
        "¿Quieres completar presupuesto, tiempo y espacio para comparar con palabras sencillas?"
        if context.is_beginner
        else "¿Qué dato faltante o compensación deseas revisar antes de considerar un modelo?"
    )
    return BusinessModelComparisonResult(
        comparison_id=new_internal_id(),
        version=BUSINESS_MODEL_ENGINE_VERSION,
        assessed_at=assessed_at,
        assessments=assessments,
        confidence=confidence,
        compatible_models=compatible,
        incompatible_models=incompatible,
        consideration_model=consideration,
        consideration_reason=reason,
        alternatives=alternatives,
        missing_data=missing,
        continuation_question=question,
        simplified_for_beginner=context.is_beginner,
    )


__all__ = ["BUSINESS_MODEL_ENGINE_VERSION", "comparar_modelos_operativos"]
