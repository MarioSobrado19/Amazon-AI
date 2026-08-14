"""Objetos inmutables cuya identidad depende de su valor."""

from domain.value_objects.money import Money
from domain.value_objects.percentage import Percentage
from domain.value_objects.frozen_mapping import FrozenMapping
from domain.value_objects.region import Region
from domain.value_objects.capability_declaration import CapabilityDeclaration
from domain.value_objects.constraint_declaration import ConstraintDeclaration
from domain.value_objects.goal_context_snapshot import GoalContextSnapshot
from domain.value_objects.preference_declaration import PreferenceDeclaration
from domain.value_objects.resource_availability import ResourceAvailability
from domain.value_objects.domain_node_reference import DomainNodeReference
from domain.value_objects.research_need import ResearchNeed
from domain.value_objects.research_question import ResearchQuestion

__all__ = [
    "CapabilityDeclaration",
    "ConstraintDeclaration",
    "FrozenMapping",
    "GoalContextSnapshot",
    "Money",
    "Percentage",
    "PreferenceDeclaration",
    "Region",
    "ResourceAvailability",
    "DomainNodeReference",
    "ResearchNeed",
    "ResearchQuestion",
]
