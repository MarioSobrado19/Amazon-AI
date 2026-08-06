from enum import Enum


class DecisionState(str, Enum):
    """Estados del recorrido de decisión definidos por el dominio."""

    EXPLORE = "explorar"
    INVESTIGATE = "investigar"
    COMPARE = "comparar"
    POSTPONE = "posponer"
    TEST = "probar"  # Reservado para fases futuras con evidencia verificada.

