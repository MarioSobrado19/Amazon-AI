from dataclasses import dataclass

from domain.entities._validation import optional_text, required_text
from domain.entities.product import Product
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True, eq=False)
class Opportunity:
    """Evaluación contextual de un Product; Marketplace puede estar pendiente."""

    opportunity_id: str
    product: Product
    marketplace_id: str | None = None
    supplier_id: str | None = None

    def __post_init__(self):
        object.__setattr__(
            self,
            "opportunity_id",
            required_text(self.opportunity_id, "opportunity_id"),
        )
        if not isinstance(self.product, Product):
            raise DomainValidationError("product debe referenciar un Product válido.")
        object.__setattr__(
            self,
            "marketplace_id",
            optional_text(self.marketplace_id, "marketplace_id"),
        )
        object.__setattr__(
            self,
            "supplier_id",
            optional_text(self.supplier_id, "supplier_id"),
        )

    def __eq__(self, other):
        if not isinstance(other, Opportunity):
            return NotImplemented
        return self.opportunity_id == other.opportunity_id

    def __hash__(self):
        return hash(self.opportunity_id)

    def to_dict(self):
        return {
            "opportunity_id": self.opportunity_id,
            "product": self.product.to_dict(),
            "marketplace_id": self.marketplace_id,
            "supplier_id": self.supplier_id,
        }

