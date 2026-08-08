from enum import Enum


class OperationalLoad(str, Enum):
    """Carga operativa cualitativa; no representa un score de ajuste."""

    LOW = "baja"
    MEDIUM = "media"
    HIGH = "alta"
    VARIABLE = "variable"

