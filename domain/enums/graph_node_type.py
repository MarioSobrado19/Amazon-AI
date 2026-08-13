from enum import Enum


class GraphNodeType(str, Enum):
    """Tipos de referencia soportados por Opportunity Graph V1."""

    OBJECTIVE = "objective"
    BUSINESS_PATH = "business_path"
    CANDIDATE_BUSINESS_PATH = "candidate_business_path"
    OPPORTUNITY = "opportunity"
    OPPORTUNITY_SCENARIO = "opportunity_scenario"
    PRODUCT = "product"
    MARKETPLACE = "marketplace"
    BUSINESS_MODEL = "business_model"
    RESULT = "result"
    RECOMMENDATION = "recommendation"
