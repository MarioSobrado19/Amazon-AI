from dataclasses import dataclass
from decimal import Decimal

from domain.exceptions import DomainValidationError
from domain.value_objects._decimal import validated_decimal


@dataclass(frozen=True, slots=True)
class Money:
    """Cantidad inmutable; solo admite aritmética con la misma moneda."""

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        amount = validated_decimal(self.amount, "amount")
        if not isinstance(self.currency, str):
            raise DomainValidationError("currency debe ser un código de tres letras.")
        currency = self.currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise DomainValidationError("currency debe ser un código de tres letras.")
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "currency", currency)

    def to_dict(self):
        return {"amount": str(self.amount), "currency": self.currency}

    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def _require_same_currency(self, other):
        if self.currency != other.currency:
            raise DomainValidationError(
                "No se pueden operar monedas distintas sin conversión explícita."
            )
