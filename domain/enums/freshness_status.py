from enum import Enum


class FreshnessStatus(str, Enum):
    """Estado de vigencia declarado por una política externa versionada."""

    CURRENT = "vigente"
    EXPIRING = "proxima_a_expirar"
    EXPIRED = "expirada"
    UNKNOWN = "desconocida"
    CONFLICTING = "en_conflicto"

