"""Objetos inmutables cuya identidad depende de su valor."""

from domain.value_objects.money import Money
from domain.value_objects.percentage import Percentage
from domain.value_objects.frozen_mapping import FrozenMapping
from domain.value_objects.region import Region

__all__ = ["FrozenMapping", "Money", "Percentage", "Region"]
