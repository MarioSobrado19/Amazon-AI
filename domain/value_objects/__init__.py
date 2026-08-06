"""Objetos inmutables cuya identidad depende de su valor."""

from domain.value_objects.money import Money
from domain.value_objects.percentage import Percentage

__all__ = ["Money", "Percentage"]
