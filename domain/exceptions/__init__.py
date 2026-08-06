"""Excepciones propias del modelo de dominio."""


class DomainError(Exception):
    """Error base del dominio de Oriva."""


class DomainValidationError(DomainError, ValueError):
    """Indica que un objeto no satisface una invariante del dominio."""

