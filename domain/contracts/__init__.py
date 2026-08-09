"""Contratos internos aún no conectados con los motores actuales."""

from domain.contracts.analysis_result import AnalysisResult
from domain.contracts.decision_recommendation import DecisionRecommendation
from domain.contracts.opportunity_result import OpportunityResult
from domain.contracts.business_model_assessment import BusinessModelAssessment
from domain.contracts.business_model_comparison_result import BusinessModelComparisonResult
from domain.contracts.business_model_context import BusinessModelContext
from domain.contracts.business_model_dimension_evaluation import (
    BusinessModelDimensionEvaluation,
)
from domain.contracts.marketplace_catalog_result import MarketplaceCatalogResult
from domain.contracts.marketplace_catalog_issue import MarketplaceCatalogIssue
from domain.contracts.opportunity_scenario_result import OpportunityScenarioResult

__all__ = [
    "AnalysisResult",
    "BusinessModelAssessment",
    "BusinessModelComparisonResult",
    "BusinessModelContext",
    "BusinessModelDimensionEvaluation",
    "DecisionRecommendation",
    "MarketplaceCatalogResult",
    "MarketplaceCatalogIssue",
    "OpportunityResult",
    "OpportunityScenarioResult",
]
