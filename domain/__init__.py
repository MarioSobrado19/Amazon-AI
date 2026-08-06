"""Lenguaje de dominio estable e independiente de infraestructura."""

from domain.contracts import AnalysisResult, DecisionRecommendation, OpportunityResult
from domain.entities import Opportunity, Product, Recommendation, Result
from domain.enums import ConfidenceLevel, DecisionState, EvidenceType, RiskLevel
from domain.exceptions import DomainError, DomainValidationError
from domain.value_objects import Money, Percentage

__all__ = [
    "AnalysisResult",
    "ConfidenceLevel",
    "DecisionRecommendation",
    "DecisionState",
    "DomainError",
    "DomainValidationError",
    "EvidenceType",
    "Money",
    "Opportunity",
    "OpportunityResult",
    "Percentage",
    "Product",
    "Recommendation",
    "Result",
    "RiskLevel",
]
