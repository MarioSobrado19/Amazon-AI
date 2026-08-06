from dataclasses import dataclass
from decimal import Decimal

from domain.value_objects._decimal import validated_decimal


@dataclass(frozen=True, slots=True)
class Percentage:
    """Porcentaje finito; permite negativos para métricas como ROI."""

    value: Decimal

    def __post_init__(self):
        object.__setattr__(self, "value", validated_decimal(self.value, "value"))

    def to_dict(self):
        return {"value": str(self.value)}

