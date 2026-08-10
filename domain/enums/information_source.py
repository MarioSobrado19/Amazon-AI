from enum import Enum


class InformationSource(str, Enum):
    """Procedencia de información contextual conservada por el dominio."""

    USER_DECLARED = "declarada_por_usuario"
    INFERRED = "inferida"
    EXTERNAL = "fuente_externa"
