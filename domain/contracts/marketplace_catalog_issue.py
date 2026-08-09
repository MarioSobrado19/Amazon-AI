from dataclasses import dataclass

from domain.entities._marketplace_validation import optional_text, required_text
from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class MarketplaceCatalogIssue:
    """Incidencia funcional serializable, sin excepciones de infraestructura."""

    code: str
    message: str
    source: str | None = None
    retryable: bool = False

    def __post_init__(self):
        object.__setattr__(self, "code", required_text(self.code, "code"))
        object.__setattr__(self, "message", required_text(self.message, "message"))
        object.__setattr__(self, "source", optional_text(self.source, "source"))
        if not isinstance(self.retryable, bool):
            raise DomainValidationError("retryable debe ser booleano.")

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "source": self.source,
            "retryable": self.retryable,
        }
