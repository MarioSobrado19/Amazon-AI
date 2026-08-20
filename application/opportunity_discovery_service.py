"""Orquestación determinista de DiscoverySignal a OpportunityHypothesis.

INTERNAL / CONFIDENTIAL — ORIVA. El servicio no descubre por sí mismo, no
puntúa, no recomienda y no promueve hipótesis a Opportunity/BusinessPath.
"""

from datetime import datetime

from application.discovery_models import (
    DiscoveryRequest,
    DiscoveryRunResult,
    DiscoveryRunStatus,
    DiscoverySignal,
    DiscoverySignalType,
    DiscoverySourceResult,
    DiscoverySourceStatus,
    HypothesisIdentityKind,
    OpportunityHypothesis,
    OpportunityHypothesisState,
    normalize_identity,
)
from domain.enums import EvidenceType, FreshnessStatus, ResearchCategory, VerificationStatus
from domain.value_objects import ResearchNeed


DISCOVERY_METHODOLOGY_VERSION = "opportunity-discovery/1.0"
_PRESENCE_TYPES = {
    DiscoverySignalType.CATALOG_PRESENCE,
    DiscoverySignalType.COMMERCIAL_LISTING_PRESENCE,
    DiscoverySignalType.MARKETPLACE_PRESENCE,
}
_UNKNOWN_BY_CATEGORY = {
    ResearchCategory.DEMAND: "demanda comercial verificable",
    ResearchCategory.COMPETITION: "oferta comercial comparable y competencia",
    ResearchCategory.SUPPLIER: "proveedor, MOQ, lead time y términos",
    ResearchCategory.MARKETPLACE: "condiciones y elegibilidad del marketplace",
    ResearchCategory.COSTS: "coste puesto y economía unitaria completa",
    ResearchCategory.RESTRICTIONS: "restricciones legales, de seguridad y plataforma",
    ResearchCategory.LOGISTICS: "fulfillment, almacenamiento, devoluciones y carga operativa",
}


def _freshness(signals: tuple[DiscoverySignal, ...]) -> FreshnessStatus:
    states = {item.freshness for item in signals}
    if FreshnessStatus.CONFLICTING in states:
        return FreshnessStatus.CONFLICTING
    if states == {FreshnessStatus.EXPIRED}:
        return FreshnessStatus.EXPIRED
    if FreshnessStatus.CURRENT in states:
        return FreshnessStatus.EXPIRING if FreshnessStatus.EXPIRED in states else FreshnessStatus.CURRENT
    if FreshnessStatus.EXPIRING in states:
        return FreshnessStatus.EXPIRING
    return FreshnessStatus.UNKNOWN


def _verification(signals: tuple[DiscoverySignal, ...]) -> VerificationStatus:
    states = {item.verification_status for item in signals}
    for state in (VerificationStatus.DISPUTED, VerificationStatus.UNVERIFIED, VerificationStatus.PARTIAL):
        if state in states:
            return state
    return VerificationStatus.VERIFIED


def _research_needs(subject_id: str, request: DiscoveryRequest, signals: tuple[DiscoverySignal, ...]) -> tuple[ResearchNeed, ...]:
    signal_types = tuple(sorted({item.signal_type.value for item in signals}))
    known = [f"Señales disponibles: {', '.join(signal_types)}."]
    if request.future_capital_ceiling_usd is not None:
        known.append(f"Techo futuro declarado: USD {request.future_capital_ceiling_usd}; no es autorización de gasto.")
    known.append(f"Capital autorizado actualmente: USD {request.currently_authorized_capital_usd}.")
    if request.horizon_days is not None:
        known.append(f"Horizonte declarado para investigación: {request.horizon_days} días.")
    needs = []
    for category, missing in _UNKNOWN_BY_CATEGORY.items():
        reason = f"La hipótesis requiere investigar {missing} sin inferirlo desde señales de discovery."
        needs.append(ResearchNeed(
            "opportunity_hypothesis",
            subject_id,
            category,
            reason,
            "high",
            True,
            (EvidenceType.DATA,),
            tuple(known),
            (missing,),
            semantic_version="discovery-needs/1.0",
        ))
    return tuple(needs)


def _make_hypothesis(request: DiscoveryRequest, signals: tuple[DiscoverySignal, ...]) -> OpportunityHypothesis:
    first = signals[0]
    signal_types = {item.signal_type for item in signals}
    contradictions = tuple(sorted({value for item in signals for value in item.contradictions}))
    freshness = _freshness(signals)
    if contradictions:
        state = OpportunityHypothesisState.CONTRADICTED
    elif freshness is FreshnessStatus.EXPIRED:
        state = OpportunityHypothesisState.STALE
    elif len(signal_types) >= 2 and signal_types & _PRESENCE_TYPES:
        state = OpportunityHypothesisState.RESEARCH_READY
    else:
        state = OpportunityHypothesisState.SURFACED
    marketplaces = tuple(sorted({item.marketplace_id for item in signals if item.marketplace_id}))
    identity = OpportunityHypothesis(
        first.identity_kind,
        first.identity_value,
        signals,
        (),
        max(item.observed_at for item in signals),
        freshness,
        _verification(signals),
        state,
        DISCOVERY_METHODOLOGY_VERSION,
        tuple(filter(None, (
            f"Se observaron {len(signal_types)} tipos de señal no redundantes: {', '.join(sorted(item.value for item in signal_types))}.",
            "Existe una señal de presencia comercial/catalogada." if signal_types & _PRESENCE_TYPES else "La señal todavía no acredita presencia comercial/catalogada.",
        ))),
        tuple(_UNKNOWN_BY_CATEGORY.values()),
        contradictions,
        first.region,
        marketplaces,
        tuple(sorted({limitation for item in signals for limitation in item.limitations} | {
            "Discovery identifica una hipótesis investigable; no demuestra demanda, ventas, rentabilidad ni autorización para ejecutar.",
        })),
    )
    return OpportunityHypothesis(
        identity.identity_kind,
        identity.identity_value,
        identity.signals,
        _research_needs(identity.hypothesis_id, request, signals),
        identity.observed_at,
        identity.freshness,
        identity.verification_status,
        identity.state,
        identity.method_version,
        identity.why_surfaced,
        identity.unknowns,
        identity.contradictions,
        identity.region,
        identity.potential_marketplaces,
        identity.limitations,
        identity.hypothesis_id,
    )


def discover_opportunity_hypotheses(
    request: DiscoveryRequest,
    sources,
    *,
    generated_at: datetime,
) -> DiscoveryRunResult:
    """Coordina fuentes suministradas; nunca inventa una señal o identidad."""
    source_results = []
    warnings = []
    missing = []
    signals_by_id = {}
    for source in tuple(sources):
        source_id = getattr(source, "source_id", source.__class__.__name__)
        try:
            result = source.collect(request)
            if not isinstance(result, DiscoverySourceResult):
                raise TypeError("La fuente no devolvió DiscoverySourceResult.")
        except Exception as error:  # frontera: no filtra texto/secretos del error externo
            result = DiscoverySourceResult(
                str(source_id),
                DiscoverySourceStatus.TECHNICAL_FAILURE,
                generated_at,
                missing_information=("La fuente no pudo ejecutarse; esto no es evidencia comercial negativa.",),
                warnings=("Fallo técnico aislado; se conservaron otras señales válidas.",),
                error_code=error.__class__.__name__,
            )
        source_results.append(result)
        warnings.extend(result.warnings)
        missing.extend(result.missing_information)
        for signal in result.signals:
            signals_by_id.setdefault(signal.signal_id, signal)

    groups = {}
    for signal in signals_by_id.values():
        key = (
            signal.identity_kind,
            normalize_identity(signal.identity_value),
            signal.region.country_code if signal.region else None,
        )
        groups.setdefault(key, []).append(signal)
    hypotheses = [_make_hypothesis(request, tuple(sorted(items, key=lambda item: item.signal_id))) for _, items in sorted(groups.items(), key=lambda item: (item[0][0].value, item[0][1], item[0][2] or ""))]
    hypotheses = tuple(sorted(hypotheses, key=lambda item: item.hypothesis_id)[:request.max_hypotheses])
    real = tuple(item for item in hypotheses if item.is_real)
    failures = any(item.status is DiscoverySourceStatus.TECHNICAL_FAILURE for item in source_results)
    if 3 <= len(real) <= request.max_hypotheses and all(item.state is OpportunityHypothesisState.RESEARCH_READY for item in real):
        status = DiscoveryRunStatus.PARTIAL if failures else DiscoveryRunStatus.HYPOTHESES_IDENTIFIED
    elif hypotheses:
        status = DiscoveryRunStatus.HOLD_EVIDENCE_ACQUISITION
        missing.append("Faltan 3–10 hipótesis reales, recientes y con identidad comercial suficiente.")
    elif failures and all(item.status is DiscoverySourceStatus.TECHNICAL_FAILURE for item in source_results):
        status = DiscoveryRunStatus.TECHNICAL_FAILURE
    else:
        status = DiscoveryRunStatus.NO_DATA
        missing.append("Ninguna fuente suministró señales legítimas con identidad investigable.")
    if request.currently_authorized_capital_usd == 0:
        warnings.append("Capital autorizado USD 0: discovery no habilita gasto, inventario, listings ni contacto con proveedores.")
    if any(not item.is_real for item in hypotheses):
        warnings.append("Fixtures, Sandbox y simulaciones pueden validar el pipeline, pero no son evidencia comercial real.")
    return DiscoveryRunResult(
        request.request_id,
        status,
        hypotheses,
        tuple(source_results),
        generated_at,
        tuple(missing),
        tuple(warnings),
        DISCOVERY_METHODOLOGY_VERSION,
    )


__all__ = ["DISCOVERY_METHODOLOGY_VERSION", "discover_opportunity_hypotheses"]
