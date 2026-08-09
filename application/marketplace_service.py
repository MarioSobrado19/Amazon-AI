from datetime import datetime, timezone

from application.ports import MarketplaceAdapter, MarketplaceAdapterError
from domain.contracts import MarketplaceCatalogIssue, MarketplaceCatalogResult
from domain.entities import BusinessModel, Marketplace, MarketplaceConditionSnapshot
from domain.entities._identity import new_internal_id
from domain.enums import ConfidenceLevel, FreshnessStatus
from domain.exceptions import DomainValidationError
from domain.value_objects import FrozenMapping, Region


MARKETPLACE_ENGINE_VERSION = "marketplace-engine/1.0"
_CONFIDENCE_RANK = {
    ConfidenceLevel.LOW: 0,
    ConfidenceLevel.MEDIUM: 1,
    ConfidenceLevel.HIGH: 2,
}


def _unique_text(*groups):
    return tuple(dict.fromkeys(item for group in groups for item in group))


def _safe_adapter_call(adapter, operation, callback, default, issues):
    try:
        return callback()
    except MarketplaceAdapterError as error:
        issues.append(
            MarketplaceCatalogIssue(
                code=error.code,
                message=f"{operation}: {error}",
                source=adapter.adapter_id,
                retryable=error.retryable,
            )
        )
    except Exception as error:
        issues.append(
            MarketplaceCatalogIssue(
                code="unexpected_adapter_error",
                message=f"{operation}: {type(error).__name__}",
                source=adapter.adapter_id,
                retryable=False,
            )
        )
    return default


def _lowest_confidence(values):
    if not values:
        return ConfidenceLevel.LOW
    return min(values, key=lambda value: _CONFIDENCE_RANK[value])


def _catalog_confidence(marketplace, models, snapshots, issues):
    if marketplace is None or issues:
        return ConfidenceLevel.LOW
    confidence = _lowest_confidence(
        [marketplace.confidence]
        + [model.confidence for model in models]
        + [item.confidence for item in snapshots]
    )
    freshness = {item.freshness for item in snapshots}
    if not snapshots or FreshnessStatus.EXPIRED in freshness or FreshnessStatus.UNKNOWN in freshness:
        return ConfidenceLevel.LOW
    if FreshnessStatus.EXPIRING in freshness or FreshnessStatus.CONFLICTING in freshness:
        return _lowest_confidence([confidence, ConfidenceLevel.MEDIUM])
    return confidence


def _freshness_details(snapshots):
    counts = {status.value: 0 for status in FreshnessStatus}
    for item in snapshots:
        counts[item.freshness.value] += 1
    return FrozenMapping.from_mapping(counts)


def _freshness_warnings(snapshots):
    warnings = []
    labels = {
        FreshnessStatus.EXPIRING: "Hay condiciones próximas a expirar.",
        FreshnessStatus.EXPIRED: "Hay condiciones expiradas; se conservan como historial.",
        FreshnessStatus.UNKNOWN: "Hay condiciones con vigencia desconocida.",
        FreshnessStatus.CONFLICTING: "Hay condiciones externas en conflicto.",
    }
    for status, message in labels.items():
        if any(item.freshness is status for item in snapshots):
            warnings.append(message)
    return tuple(warnings)


def crear_catalogo_marketplace(
    adapter: MarketplaceAdapter,
    region: Region,
    *,
    generated_at: datetime | None = None,
):
    """Coordina datos normalizados sin consultar fuentes ni evaluar modelos."""

    if not isinstance(region, Region):
        raise DomainValidationError("region debe ser una Region válida.")
    generated_at = generated_at or datetime.now(timezone.utc)
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise DomainValidationError("generated_at debe incluir zona horaria.")
    adapter_id = getattr(adapter, "adapter_id", None)
    if not isinstance(adapter_id, str) or not adapter_id.strip():
        raise DomainValidationError("adapter debe declarar adapter_id.")

    issues = []
    warnings = []
    missing = []
    unavailable = []
    marketplace = _safe_adapter_call(
        adapter,
        "obtener identidad",
        lambda: adapter.get_marketplace(region),
        None,
        issues,
    )

    if marketplace is None:
        missing.append("marketplace")
        unavailable.append("No hay marketplace disponible para la región solicitada.")
        return MarketplaceCatalogResult(
            catalog_id=new_internal_id(),
            version=MARKETPLACE_ENGINE_VERSION,
            generated_at=generated_at,
            unavailable_reasons=tuple(unavailable),
            warnings=tuple(warnings),
            missing_data=tuple(missing),
            functional_errors=tuple(issues),
            freshness_summary=_freshness_details(()),
            sources=(adapter_id,),
            confidence=ConfidenceLevel.LOW,
        )
    if not isinstance(marketplace, Marketplace):
        raise DomainValidationError("El adaptador devolvió un marketplace inválido.")
    if marketplace.region != region:
        unavailable.append("La región solicitada no es compatible con el marketplace.")
        missing.append("compatible_marketplace_region")
        issues.append(
            MarketplaceCatalogIssue(
                code="incompatible_region",
                message="La región solicitada no coincide con la región del marketplace.",
                source=adapter_id,
                retryable=False,
            )
        )
        return MarketplaceCatalogResult(
            catalog_id=new_internal_id(),
            version=MARKETPLACE_ENGINE_VERSION,
            generated_at=generated_at,
            unavailable_reasons=tuple(unavailable),
            missing_data=tuple(missing),
            functional_errors=tuple(issues),
            freshness_summary=_freshness_details(()),
            sources=_unique_text((adapter_id,), (marketplace.source,)),
            confidence=ConfidenceLevel.LOW,
        )

    models = tuple(
        _safe_adapter_call(
            adapter,
            "listar modelos operativos",
            lambda: adapter.list_business_models(marketplace, region),
            (),
            issues,
        )
    )
    snapshots = tuple(
        _safe_adapter_call(
            adapter,
            "obtener condiciones",
            lambda: adapter.list_condition_snapshots(marketplace, region),
            (),
            issues,
        )
    )
    requirements = tuple(
        _safe_adapter_call(
            adapter,
            "consultar requisitos",
            lambda: adapter.list_requirements(marketplace, region),
            (),
            issues,
        )
    )
    restrictions = tuple(
        _safe_adapter_call(
            adapter,
            "consultar restricciones",
            lambda: adapter.list_restrictions(marketplace, region),
            (),
            issues,
        )
    )
    capabilities = tuple(
        _safe_adapter_call(
            adapter,
            "obtener capacidades",
            lambda: adapter.list_capabilities(marketplace, region),
            (),
            issues,
        )
    )

    if any(not isinstance(item, BusinessModel) for item in models):
        raise DomainValidationError("El adaptador devolvió modelos inválidos.")
    if any(not isinstance(item, MarketplaceConditionSnapshot) for item in snapshots):
        raise DomainValidationError("El adaptador devolvió snapshots inválidos.")
    compatible_models = tuple(
        item
        for item in models
        if item.region == region
        and item.marketplace_id in (None, marketplace.marketplace_id)
    )
    compatible_snapshots = tuple(
        item
        for item in snapshots
        if item.region == region
        and item.marketplace.marketplace_id == marketplace.marketplace_id
    )
    if len(compatible_models) != len(models):
        warnings.append("Se omitieron modelos incompatibles con el contexto solicitado.")
        missing.append("compatible_business_models")
    if len(compatible_snapshots) != len(snapshots):
        warnings.append("Se omitieron condiciones incompatibles con el contexto solicitado.")
        missing.append("compatible_condition_snapshots")
    if not compatible_models:
        missing.append("business_models")
        warnings.append("No hay modelos operativos disponibles para el contexto solicitado.")
    if not compatible_snapshots:
        missing.append("condition_snapshots")
        warnings.append("No hay condiciones verificables disponibles para el contexto solicitado.")
    warnings.extend(_freshness_warnings(compatible_snapshots))

    all_requirements = _unique_text(
        marketplace.general_requirements,
        requirements,
        *(item.requirements for item in compatible_models),
    )
    all_restrictions = _unique_text(
        marketplace.general_restrictions,
        restrictions,
        *(item.restrictions for item in compatible_models),
    )
    all_capabilities = _unique_text(marketplace.capabilities, capabilities)
    sources = _unique_text(
        (adapter_id, marketplace.source),
        *(tuple(filter(None, (item.source,))) for item in compatible_models),
        *((item.source,) for item in compatible_snapshots),
    )

    return MarketplaceCatalogResult(
        catalog_id=new_internal_id(),
        version=MARKETPLACE_ENGINE_VERSION,
        generated_at=generated_at,
        marketplaces=(marketplace,),
        business_models=compatible_models,
        snapshots=compatible_snapshots,
        unavailable_reasons=tuple(unavailable),
        warnings=_unique_text(tuple(warnings)),
        requirements=all_requirements,
        restrictions=all_restrictions,
        capabilities=all_capabilities,
        missing_data=_unique_text(tuple(missing)),
        functional_errors=tuple(issues),
        freshness_summary=_freshness_details(compatible_snapshots),
        sources=sources,
        confidence=_catalog_confidence(
            marketplace, compatible_models, compatible_snapshots, issues
        ),
    )


__all__ = ["MARKETPLACE_ENGINE_VERSION", "crear_catalogo_marketplace"]
