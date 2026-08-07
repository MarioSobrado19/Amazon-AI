"""Adaptadores de representación para el Decision Engine, sin reglas de decisión."""

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from application.adapters.opportunity_domain_adapter import (
    construir_oportunidad_desde_formato_actual,
    convertir_oportunidad_a_formato_actual,
)
from domain.contracts import AnalysisResult, DecisionRecommendation, OpportunityResult
from domain.entities import Recommendation
from domain.enums import ConfidenceLevel, DecisionState, RiskLevel
from domain.exceptions import DomainValidationError


DECISION_VERSION = "1"


def _stable_id(prefix, value):
    return f"{prefix}-{uuid5(NAMESPACE_URL, f'oriva:{prefix}:{value}')}"


def construir_analisis_decision(resultados, analysis_id="decision-analysis"):
    """Convierte resultados heredados a contratos oficiales sin recalcularlos."""
    if not isinstance(resultados, list):
        raise DomainValidationError("resultados debe ser una lista.")
    opportunities = []
    for producto in resultados:
        opportunity = construir_oportunidad_desde_formato_actual(producto)
        opportunities.append(
            OpportunityResult(opportunity, opportunity.financial_context)
        )
    return AnalysisResult(analysis_id=analysis_id, opportunities=tuple(opportunities))


def convertir_resultados_a_formato_actual(opportunity_results):
    """Convierte contratos del dominio al formato heredado esperado por Application."""
    items = tuple(opportunity_results)
    if any(not isinstance(item, OpportunityResult) for item in items):
        raise DomainValidationError(
            "opportunity_results debe contener OpportunityResult válidos."
        )
    return [
        convertir_oportunidad_a_formato_actual(item.opportunity) for item in items
    ]


def construir_recomendacion_dominio(
    decision,
    opportunity_results=(),
    primary_opportunity_id=None,
    created_at=None,
):
    """Representa una salida heredada mediante Recommendation y su contrato."""
    if not isinstance(decision, dict):
        raise DomainValidationError("decision debe ser un diccionario.")
    required = {
        "estado", "recomendacion_principal", "resumen", "evidencia_favorable",
        "riesgos", "datos_faltantes", "proximo_paso", "alternativas",
        "condiciones_para_avanzar", "nivel_confianza", "reglas_aplicadas",
        "limitaciones", "pregunta_de_continuacion", "contexto_utilizado",
    }
    missing = sorted(required - set(decision))
    if missing:
        raise DomainValidationError(
            f"decision no contiene propiedades requeridas: {', '.join(missing)}."
        )
    opportunity_results = tuple(opportunity_results)
    if any(not isinstance(item, OpportunityResult) for item in opportunity_results):
        raise DomainValidationError(
            "opportunity_results debe contener OpportunityResult válidos."
        )
    source_results = tuple(
        result for item in opportunity_results for result in item.results
    )
    if primary_opportunity_id is not None:
        known_ids = {
            item.opportunity.opportunity_id for item in opportunity_results
        }
        if primary_opportunity_id not in known_ids:
            raise DomainValidationError(
                "primary_opportunity_id debe referenciar una oportunidad utilizada."
            )
    created_at = created_at or (
        opportunity_results[0].opportunity.evaluated_at
        if opportunity_results else datetime.now(timezone.utc)
    )
    identity = (
        decision["estado"], decision["recomendacion_principal"],
        decision["resumen"], tuple(decision["reglas_aplicadas"]),
        tuple(sorted(decision["contexto_utilizado"].items())),
        primary_opportunity_id,
    )
    recommendation = Recommendation(
        recommendation_id=_stable_id("recommendation", identity),
        state=DecisionState(decision["estado"]),
        message=decision["recomendacion_principal"],
        explanation=decision["resumen"],
        confidence=ConfidenceLevel(decision["nivel_confianza"]),
        evidence=source_results,
        risks=tuple((RiskLevel.MEDIUM, item) for item in decision["riesgos"]),
        limitations=tuple(decision["limitaciones"]),
        opportunity_id=primary_opportunity_id,
        favorable_evidence=tuple(decision["evidencia_favorable"]),
        missing_data=tuple(decision["datos_faltantes"]),
        next_step=decision["proximo_paso"],
        alternatives=tuple(decision["alternativas"]),
        conditions_to_advance=tuple(decision["condiciones_para_avanzar"]),
        applied_rules=tuple(decision["reglas_aplicadas"]),
        continuation_question=decision["pregunta_de_continuacion"],
        context_used=tuple(decision["contexto_utilizado"].items()),
        version=DECISION_VERSION,
        created_at=created_at,
    )
    return DecisionRecommendation(
        recommendation=recommendation,
        missing_data=recommendation.missing_data,
        conditions_to_advance=recommendation.conditions_to_advance,
    )


def convertir_recomendacion_a_formato_actual(contract):
    """Restaura exactamente el contrato heredado que consume la UI."""
    if not isinstance(contract, DecisionRecommendation):
        raise DomainValidationError("contract debe ser DecisionRecommendation válido.")
    item = contract.recommendation
    return {
        "estado": item.state.value,
        "recomendacion_principal": item.message,
        "resumen": item.explanation,
        "evidencia_favorable": list(item.favorable_evidence),
        "riesgos": [explanation for _, explanation in item.risks],
        "datos_faltantes": list(item.missing_data),
        "proximo_paso": item.next_step,
        "alternativas": list(item.alternatives),
        "condiciones_para_avanzar": list(item.conditions_to_advance),
        "nivel_confianza": item.confidence.value,
        "reglas_aplicadas": list(item.applied_rules),
        "limitaciones": list(item.limitations),
        "pregunta_de_continuacion": item.continuation_question,
        "contexto_utilizado": dict(item.context_used),
    }
