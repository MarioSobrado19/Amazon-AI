from enum import Enum


class ConfidenceLevel(str, Enum):
    """Grado de confianza declarado para evidencia o conclusiones."""

    LOW = "bajo"
    MEDIUM = "medio"
    HIGH = "alto"

