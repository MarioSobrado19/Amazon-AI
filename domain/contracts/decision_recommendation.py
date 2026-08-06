from dataclasses import dataclass

from domain.entities import Recommendation
from domain.entities._validation import required_text
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class DecisionRecommendation:
    """Recomendación junto con datos faltantes y condiciones para avanzar."""

    recommendation: Recommendation
    missing_data: tuple[str, ...] = ()
    conditions_to_advance: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.recommendation, Recommendation):
            raise DomainValidationError("recommendation debe ser válida.")
        object.__setattr__(
            self,
            "missing_data",
            tuple(required_text(item, "missing_data") for item in self.missing_data),
        )
        object.__setattr__(
            self,
            "conditions_to_advance",
            tuple(
                required_text(item, "condition")
                for item in self.conditions_to_advance
            ),
        )

    def to_dict(self):
        return {
            "recommendation": self.recommendation.to_dict(),
            "missing_data": list(self.missing_data),
            "conditions_to_advance": list(self.conditions_to_advance),
        }

