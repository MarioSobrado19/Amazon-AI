"""Valores enumerados compartidos por el dominio."""

from domain.enums.confidence_level import ConfidenceLevel
from domain.enums.decision_state import DecisionState
from domain.enums.evidence_type import EvidenceType
from domain.enums.risk_level import RiskLevel
from domain.enums.freshness_status import FreshnessStatus
from domain.enums.operational_load import OperationalLoad
from domain.enums.verification_status import VerificationStatus
from domain.enums.information_source import InformationSource
from domain.enums.candidate_path_state import CandidatePathState
from domain.enums.business_path_state import BusinessPathState
from domain.enums.path_promotion_action import PathPromotionAction
from domain.enums.graph_node_type import GraphNodeType
from domain.enums.evidence_relation_type import EvidenceRelationType
from domain.enums.investigation_status import InvestigationStatus
from domain.enums.research_category import ResearchCategory
from domain.enums.research_question_status import ResearchQuestionStatus
from domain.enums.conflict_resolution_status import ConflictResolutionStatus

__all__ = [
    "ConfidenceLevel",
    "CandidatePathState",
    "BusinessPathState",
    "DecisionState",
    "EvidenceType",
    "FreshnessStatus",
    "InformationSource",
    "OperationalLoad",
    "PathPromotionAction",
    "RiskLevel",
    "VerificationStatus",
    "GraphNodeType",
    "EvidenceRelationType",
    "InvestigationStatus",
    "ResearchCategory",
    "ResearchQuestionStatus",
    "ConflictResolutionStatus",
]
