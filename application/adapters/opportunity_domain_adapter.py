"""Traducción sin cálculos entre diccionarios actuales y entidades de dominio."""

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from domain.entities import Opportunity, Product, Result
from domain.enums import ConfidenceLevel, EvidenceType
from domain.exceptions import DomainValidationError


SOURCE_FINANCIAL = "Financial Engine"
SOURCE_OPPORTUNITY = "Opportunity Engine"
FINANCIAL_VERSION = "1"
OPPORTUNITY_VERSION = "1"
OPPORTUNITY_FIELDS = {
    "opportunity_score",
    "opportunity_category",
    "opportunity_factors",
}
RESERVED_FIELDS = {
    "nombre",
    "product_id",
    "opportunity_id",
    "marketplace_id",
    "supplier_id",
}
IDENTITY_CONTEXT_FIELDS = (
    "costo_producto",
    "precio",
    "envio",
    "tarifa_amazon",
    "otros_costos",
)
FALLBACK_IDENTITY_FIELDS = ("roi", "margen", "ganancia", "evaluacion")
MAPPING_MARKER = "__oriva_mapping__"
LIST_MARKER = "__oriva_list__"
TUPLE_MARKER = "__oriva_tuple__"


def _stable_id(prefix, value):
    return f"{prefix}-{uuid5(NAMESPACE_URL, f'oriva:{prefix}:{value}')}"


def _freeze(value):
    if isinstance(value, dict):
        return (
            MAPPING_MARKER,
            tuple((str(key), _freeze(item)) for key, item in value.items()),
        )
    if isinstance(value, list):
        return (LIST_MARKER, tuple(_freeze(item) for item in value))
    if isinstance(value, tuple):
        return (TUPLE_MARKER, tuple(_freeze(item) for item in value))
    return value


def _thaw(value):
    if isinstance(value, tuple) and len(value) == 2:
        marker, content = value
        if marker == MAPPING_MARKER:
            return {key: _thaw(item) for key, item in content}
        if marker == LIST_MARKER:
            return [_thaw(item) for item in content]
        if marker == TUPLE_MARKER:
            return tuple(_thaw(item) for item in content)
    return value


def _source_and_version(field):
    if field in OPPORTUNITY_FIELDS:
        return SOURCE_OPPORTUNITY, OPPORTUNITY_VERSION
    return SOURCE_FINANCIAL, FINANCIAL_VERSION


def construir_oportunidad_desde_formato_actual(producto, evaluated_at=None):
    """Construye dominio sin modificar ni recalcular los valores recibidos."""
    if not isinstance(producto, dict):
        raise DomainValidationError("producto debe ser un diccionario.")

    name = producto.get("nombre")
    normalized_name = name.strip().casefold() if isinstance(name, str) else name
    product_id = producto.get("product_id") or _stable_id(
        "product", normalized_name
    )
    identity_fields = tuple(
        (field, _freeze(producto[field]))
        for field in IDENTITY_CONTEXT_FIELDS
        if field in producto
    )
    if not identity_fields:
        identity_fields = tuple(
            (field, _freeze(producto[field]))
            for field in FALLBACK_IDENTITY_FIELDS
            if field in producto
        )
    opportunity_seed = (
        product_id,
        producto.get("marketplace_id"),
        producto.get("supplier_id"),
        identity_fields,
    )
    opportunity_id = producto.get("opportunity_id") or _stable_id(
        "opportunity", opportunity_seed
    )
    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    product = Product(product_id=product_id, name=name)

    results = []
    for field, value in producto.items():
        if field in RESERVED_FIELDS:
            continue
        source, version = _source_and_version(field)
        results.append(
            Result(
                result_id=f"{opportunity_id}:{field}",
                name=field,
                value=_freeze(value),
                evidence_type=EvidenceType.ESTIMATE,
                source=source,
                confidence=ConfidenceLevel.MEDIUM,
                recorded_at=evaluated_at,
                version=version,
            )
        )

    return Opportunity(
        opportunity_id=opportunity_id,
        product=product,
        marketplace_id=producto.get("marketplace_id"),
        supplier_id=producto.get("supplier_id"),
        financial_context=tuple(results),
        evaluated_at=evaluated_at,
    )


def convertir_oportunidad_a_formato_actual(opportunity):
    """Devuelve una copia compatible con los consumidores heredados."""
    if not isinstance(opportunity, Opportunity):
        raise DomainValidationError("opportunity debe ser una entidad válida.")

    producto = {"nombre": opportunity.product.name}
    for result in opportunity.financial_context:
        producto[result.name] = _thaw(result.value)
    if opportunity.marketplace_id is not None:
        producto["marketplace_id"] = opportunity.marketplace_id
    if opportunity.supplier_id is not None:
        producto["supplier_id"] = opportunity.supplier_id
    return producto
