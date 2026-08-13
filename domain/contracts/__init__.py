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
from domain.contracts.goal_to_business_request import GoalToBusinessRequest
from domain.contracts.candidate_business_path import CandidateBusinessPath
from domain.contracts.goal_to_business_result import GoalToBusinessResult
from domain.contracts.path_assessment import PathAssessment, PathDimensionAssessment
from domain.contracts.business_path_promotion_result import BusinessPathPromotionResult
from domain.contracts.evidence_relation import EvidenceRelation
from domain.contracts.opportunity_graph_snapshot import OpportunityGraphSnapshot

__all__ = [
    "AnalysisResult",
    "BusinessModelAssessment",
    "BusinessPathPromotionResult",
    "BusinessModelComparisonResult",
    "BusinessModelContext",
    "BusinessModelDimensionEvaluation",
    "DecisionRecommendation",
    "GoalToBusinessRequest",
    "CandidateBusinessPath",
    "GoalToBusinessResult",
    "PathAssessment",
    "PathDimensionAssessment",
    "MarketplaceCatalogResult",
    "MarketplaceCatalogIssue",
    "OpportunityResult",
    "OpportunityScenarioResult",
    "EvidenceRelation",
    "OpportunityGraphSnapshot",
]
