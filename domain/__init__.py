"""Lenguaje de dominio estable e independiente de infraestructura."""

from domain.contracts import (
    AnalysisResult,
    BusinessModelAssessment,
    BusinessModelComparisonResult,
    BusinessModelContext,
    BusinessModelDimensionEvaluation,
    DecisionRecommendation,
    MarketplaceCatalogResult,
    MarketplaceCatalogIssue,
    OpportunityResult,
    OpportunityScenarioResult,
)
from domain.entities import (
    BusinessModel,
    Marketplace,
    MarketplaceConditionSnapshot,
    Opportunity,
    OpportunityScenario,
    Product,
    Recommendation,
    Result,
)
from domain.enums import (
    ConfidenceLevel,
    DecisionState,
    EvidenceType,
    FreshnessStatus,
    OperationalLoad,
    RiskLevel,
    VerificationStatus,
)
from domain.exceptions import DomainError, DomainValidationError
from domain.value_objects import FrozenMapping, Money, Percentage, Region

__all__ = [
    "AnalysisResult",
    "BusinessModel",
    "BusinessModelAssessment",
    "BusinessModelComparisonResult",
    "BusinessModelContext",
    "BusinessModelDimensionEvaluation",
    "ConfidenceLevel",
    "DecisionRecommendation",
    "DecisionState",
    "DomainError",
    "DomainValidationError",
    "EvidenceType",
    "FreshnessStatus",
    "FrozenMapping",
    "Marketplace",
    "MarketplaceCatalogResult",
    "MarketplaceCatalogIssue",
    "MarketplaceConditionSnapshot",
    "Money",
    "Opportunity",
    "OpportunityResult",
    "OpportunityScenario",
    "OpportunityScenarioResult",
    "OperationalLoad",
    "Percentage",
    "Product",
    "Recommendation",
    "Region",
    "Result",
    "RiskLevel",
    "VerificationStatus",
]
