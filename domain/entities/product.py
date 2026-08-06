from dataclasses import dataclass

from domain.entities._validation import optional_text, required_text
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True, eq=False)
class Product:
    """Artículo identificado sin precios, proveedor o marketplace permanentes."""

    product_id: str
    name: str
    description: str | None = None
    external_identifiers: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "product_id", required_text(self.product_id, "product_id"))
        object.__setattr__(self, "name", required_text(self.name, "name"))
        object.__setattr__(
            self,
            "description",
            optional_text(self.description, "description"),
        )
        identifiers = tuple(self.external_identifiers)
        normalized = []
        for identifier in identifiers:
            if not isinstance(identifier, tuple) or len(identifier) != 2:
                raise DomainValidationError(
                    "external_identifiers debe contener pares de tipo y valor."
                )
            kind, value = identifier
            normalized.append(
                (required_text(kind, "identifier_type"), required_text(value, "identifier_value"))
            )
        object.__setattr__(self, "external_identifiers", tuple(normalized))

    def __eq__(self, other):
        if not isinstance(other, Product):
            return NotImplemented
        return self.product_id == other.product_id

    def __hash__(self):
        return hash(self.product_id)

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "external_identifiers": dict(self.external_identifiers),
        }

