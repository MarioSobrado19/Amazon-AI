from enum import Enum


class EvidenceType(str, Enum):
    """Naturaleza de la información, sin confundir hechos con inferencias."""

    DATA = "dato"
    ESTIMATE = "estimacion"
    ASSUMPTION = "supuesto"

