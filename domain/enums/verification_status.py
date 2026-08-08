from enum import Enum


class VerificationStatus(str, Enum):
    """Grado de verificación de una condición o fuente externa."""

    UNVERIFIED = "no_verificada"
    PARTIAL = "parcialmente_verificada"
    VERIFIED = "verificada"
    DISPUTED = "disputada"

