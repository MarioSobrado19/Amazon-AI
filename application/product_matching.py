"""Matching conservador entre productos de distintas fuentes."""

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata


def _digits(value):
    return re.sub(r"\D", "", str(value or ""))


def _text(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join("".join(char for char in value if not unicodedata.combining(char)).split())


@dataclass(frozen=True)
class ProductMatch:
    matched: bool
    confidence: str
    score: float
    method: str
    explanation: str


def match_products(left, right):
    left_gtin, right_gtin = _digits(left.get("gtin") or left.get("upc")), _digits(right.get("gtin") or right.get("upc"))
    if left_gtin and right_gtin:
        if left_gtin == right_gtin:
            return ProductMatch(True, "high", 1.0, "gtin", "GTIN/UPC exacto en ambas fuentes.")
        return ProductMatch(False, "none", 0.0, "gtin_conflict", "Los GTIN/UPC observados son distintos.")
    left_name, right_name = _text(left.get("nombre")), _text(right.get("nombre"))
    similarity = SequenceMatcher(None, left_name, right_name).ratio() if left_name and right_name else 0.0
    brands_equal = bool(_text(left.get("brand"))) and _text(left.get("brand")) == _text(right.get("brand"))
    if similarity >= 0.9 and brands_equal:
        return ProductMatch(True, "medium", round(similarity, 3), "name_brand", "Nombre muy similar y marca coincidente; falta identificador sólido.")
    if similarity >= 0.8:
        return ProductMatch(False, "low", round(similarity, 3), "name_only", "Coincidencia textual posible; requiere revisión o GTIN.")
    return ProductMatch(False, "none", round(similarity, 3), "no_match", "No hay evidencia suficiente de identidad compartida.")
