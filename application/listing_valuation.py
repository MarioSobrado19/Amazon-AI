"""Valoración conservadora de listings activos comparables."""

from collections import Counter
from statistics import median
import re
import unicodedata


PRESENTATION_ASPECTS = {
    "brand": {"brand", "marca"},
    "quantity": {"number of units", "unit count", "quantity", "cantidad", "pack size"},
    "size_weight": {"size", "item weight", "weight", "volume", "tamaño", "peso"},
    "variant": {"flavor", "roast", "type", "model", "variety", "variante"},
}


def _text(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split()) or None


def _money_value(value):
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_presentation(detail, summary):
    aspects = {}
    for aspect in detail.get("localizedAspects") or []:
        name = _text(aspect.get("name"))
        if name:
            aspects[name] = _text(aspect.get("value"))
    presentation = {}
    for field, names in PRESENTATION_ASPECTS.items():
        direct = _text(detail.get(field) or summary.get(field))
        presentation[field] = direct or next(
            (aspects[name] for name in names if aspects.get(name)), None
        )
    presentation["condition"] = _text(detail.get("condition") or summary.get("condition"))
    price = detail.get("price") or {}
    presentation["currency"] = _text(
        price.get("currency") or summary.get("currency")
    )
    return presentation


def extract_shipping(detail):
    costs = []
    for option in detail.get("shippingOptions") or []:
        value = _money_value(option.get("shippingCost"))
        if value is not None:
            costs.append(value)
    return min(costs) if costs else None


def _canonical_values(listings):
    canonical = {}
    for field in ("brand", "quantity", "size_weight", "variant"):
        values = [item["presentation"].get(field) for item in listings]
        observed = [value for value in values if value]
        canonical[field] = Counter(observed).most_common(1)[0][0] if observed else None
    return canonical


def _outlier_indexes(values):
    if len(values) < 3:
        return set()
    center = median(values)
    deviations = [abs(value - center) for value in values]
    mad = median(deviations)
    if mad == 0:
        return set()
    return {
        index for index, value in enumerate(values)
        if 0.6745 * abs(value - center) / mad > 3.5
    }


def value_listings(listings, *, minimum_comparables=3, expected_condition="new", expected_currency="usd"):
    if minimum_comparables < 1:
        raise ValueError("minimum_comparables debe ser al menos 1.")
    canonical = _canonical_values(listings)
    evaluated = []
    comparable = []
    for item in listings:
        conflicts = []
        unknown = []
        presentation = item["presentation"]
        for field, expected in canonical.items():
            observed = presentation.get(field)
            if not observed:
                unknown.append(field)
            elif expected and observed != expected:
                conflicts.append(field)
        if presentation.get("condition") != _text(expected_condition):
            conflicts.append("condition")
        if presentation.get("currency") != _text(expected_currency):
            conflicts.append("currency")
        accepted = not conflicts
        record = {
            **item,
            "presentation_validation": {
                "accepted": accepted,
                "conflicts": sorted(set(conflicts)),
                "unknown": sorted(set(unknown)),
                "canonical": canonical,
            },
        }
        evaluated.append(record)
        if accepted:
            comparable.append(record)

    advertised = [item["advertised_price"] for item in comparable]
    outliers = _outlier_indexes(advertised)
    for index, item in enumerate(comparable):
        item["is_price_outlier"] = index in outliers
    usable = [item for index, item in enumerate(comparable) if index not in outliers]
    advertised_usable = [item["advertised_price"] for item in usable]
    delivered_observed = [
        item["delivered_price"] for item in comparable if item["delivered_price"] is not None
    ]
    delivered_usable = [
        item["delivered_price"] for item in usable if item["delivered_price"] is not None
    ]
    enough = len(usable) >= minimum_comparables
    confidence = "high" if len(usable) >= 5 else "medium" if enough else "low"
    return {
        "listings": evaluated,
        "comparable_count": len(comparable),
        "usable_comparable_count": len(usable),
        "minimum_comparables": minimum_comparables,
        "confidence": confidence,
        "advertised_price": {
            "minimum": min(advertised) if advertised else None,
            "maximum": max(advertised) if advertised else None,
            "observable_median": median(advertised) if advertised else None,
        },
        "delivered_price": {
            "minimum": min(delivered_observed) if delivered_observed else None,
            "maximum": max(delivered_observed) if delivered_observed else None,
            "observable_median": median(delivered_observed) if delivered_observed else None,
            "unknown_shipping_count": len(comparable) - len(delivered_observed),
        },
        "outlier_item_ids": [
            item.get("ebay_item_id") for item in comparable if item.get("is_price_outlier")
        ],
        "representative_price": median(advertised_usable) if enough else None,
        "representative_price_basis": "advertised_price_median" if enough else None,
        "limitations": ([] if enough else [
            f"Solo hay {len(usable)} listings comparables utilizables; se requieren {minimum_comparables} para un precio representativo.",
            "La mediana observable se informa descriptivamente, pero no se asume representativa del mercado.",
        ]),
    }
