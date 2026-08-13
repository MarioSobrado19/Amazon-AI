from enum import Enum


class EvidenceRelationType(str, Enum):
    """Relaciones dirigidas y genéricas del Opportunity Graph V1."""

    PURSUES = "pursues"
    ORIGINATED_FROM = "originated_from"
    EVALUATES = "evaluates"
    REPRESENTS = "represents"
    USES_SCENARIO = "uses_scenario"
    TARGETS_MARKETPLACE = "targets_marketplace"
    CONSIDERS_BUSINESS_MODEL = "considers_business_model"
    CONCERNS_PRODUCT = "concerns_product"
    SUPPORTS = "provides_evidence_for"
    ESTIMATED_BY = "estimated_by"
    DERIVED_FROM = "derived_from"
