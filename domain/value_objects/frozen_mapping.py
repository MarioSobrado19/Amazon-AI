from dataclasses import dataclass
from decimal import Decimal
from math import isfinite
from collections.abc import Mapping

from domain.exceptions import DomainValidationError


def _freeze(value):
    if isinstance(value, FrozenMapping):
        return value
    if isinstance(value, Mapping):
        return FrozenMapping(tuple(value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and isfinite(value):
        return value
    if isinstance(value, Decimal) and value.is_finite():
        return value
    raise DomainValidationError("Los valores deben ser inmutables, finitos y serializables.")


def _serialize(value):
    if isinstance(value, FrozenMapping):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    return value


@dataclass(frozen=True, slots=True)
class FrozenMapping:
    """Mapa inmutable para conservar estructuras externas sin exponer mutabilidad."""

    items: tuple[tuple[str, object], ...] = ()

    def __post_init__(self):
        normalized = []
        seen = set()
        for item in tuple(self.items):
            if not isinstance(item, tuple) or len(item) != 2:
                raise DomainValidationError("items debe contener pares de clave y valor.")
            key, value = item
            if not isinstance(key, str) or not key.strip():
                raise DomainValidationError("key es obligatorio.")
            key = key.strip()
            if key in seen:
                raise DomainValidationError(f"La clave {key} está duplicada.")
            seen.add(key)
            normalized.append((key, _freeze(value)))
        object.__setattr__(self, "items", tuple(sorted(normalized, key=lambda item: item[0])))

    @classmethod
    def from_mapping(cls, value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise DomainValidationError("value debe ser un mapa.")
        return cls(tuple(value.items()))

    def to_dict(self):
        return {key: _serialize(value) for key, value in self.items}
