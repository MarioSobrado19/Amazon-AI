"""Entidades iniciales del dominio oficial de Oriva."""

from domain.entities.opportunity import Opportunity
from domain.entities.product import Product
from domain.entities.recommendation import Recommendation
from domain.entities.result import Result
from domain.entities.business_model import BusinessModel
from domain.entities.marketplace import Marketplace
from domain.entities.marketplace_condition_snapshot import MarketplaceConditionSnapshot
from domain.entities.opportunity_scenario import OpportunityScenario
from domain.entities.objective import Objective
from domain.entities.business_path import BusinessPath

__all__ = [
    "BusinessModel",
    "BusinessPath",
    "Marketplace",
    "MarketplaceConditionSnapshot",
    "Opportunity",
    "OpportunityScenario",
    "Objective",
    "Product",
    "Recommendation",
    "Result",
]
