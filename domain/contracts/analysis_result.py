from dataclasses import dataclass

from domain.contracts.decision_recommendation import DecisionRecommendation
from domain.contracts.opportunity_result import OpportunityResult
from domain.entities._validation import required_text
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Salida interna agregada de un análisis de oportunidades."""

    analysis_id: str
    opportunities: tuple[OpportunityResult, ...] = ()
    recommendations: tuple[DecisionRecommendation, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(
            self,
            "analysis_id",
            required_text(self.analysis_id, "analysis_id"),
        )
        opportunities = tuple(self.opportunities)
        if any(not isinstance(item, OpportunityResult) for item in opportunities):
            raise DomainValidationError(
                "opportunities debe contener OpportunityResult válidos."
            )
        object.__setattr__(self, "opportunities", opportunities)

        recommendations = tuple(self.recommendations)
        if any(
            not isinstance(item, DecisionRecommendation)
            for item in recommendations
        ):
            raise DomainValidationError(
                "recommendations debe contener DecisionRecommendation válidas."
            )
        object.__setattr__(self, "recommendations", recommendations)
        object.__setattr__(
            self,
            "warnings",
            tuple(required_text(item, "warning") for item in self.warnings),
        )

    def to_dict(self):
        return {
            "analysis_id": self.analysis_id,
            "opportunities": [item.to_dict() for item in self.opportunities],
            "recommendations": [
                item.to_dict() for item in self.recommendations
            ],
            "warnings": list(self.warnings),
        }

