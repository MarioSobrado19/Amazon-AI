from enum import Enum


class ResearchCategory(str, Enum):
    DEMAND = "demand"
    COMPETITION = "competition"
    SUPPLIER = "supplier"
    MARKETPLACE = "marketplace"
    COSTS = "costs"
    RESTRICTIONS = "restrictions"
    LOGISTICS = "logistics"
