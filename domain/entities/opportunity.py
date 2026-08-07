from dataclasses import dataclass, field
from datetime import datetime, timezone

from domain.entities._validation import optional_text, required_text
from domain.entities.product import Product
from domain.entities.result import Result
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True, eq=False)
class Opportunity:
    """Evaluación contextual de un Product; Marketplace puede estar pendiente."""

    opportunity_id: str
    product: Product
    marketplace_id: str | None = None
    supplier_id: str | None = None
    financial_context: tuple[Result, ...] = ()
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

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
        financial_context = tuple(self.financial_context)
        if any(not isinstance(item, Result) for item in financial_context):
            raise DomainValidationError(
                "financial_context debe contener Result válidos."
            )
        object.__setattr__(self, "financial_context", financial_context)
        if not isinstance(self.evaluated_at, datetime):
            raise DomainValidationError("evaluated_at debe ser una fecha válida.")
        if self.evaluated_at.tzinfo is None:
            raise DomainValidationError("evaluated_at debe incluir zona horaria.")

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
            "financial_context": [
                item.to_dict() for item in self.financial_context
            ],
            "evaluated_at": self.evaluated_at.isoformat(),
        }
