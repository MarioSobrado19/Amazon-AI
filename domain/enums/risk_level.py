from enum import Enum


class RiskLevel(str, Enum):
    """Nivel cualitativo de exposición o incertidumbre."""

    LOW = "bajo"
    MEDIUM = "medio"
    HIGH = "alto"

