from uuid import UUID, uuid4

from domain.exceptions import DomainValidationError


def new_internal_id():
    """Genera una identidad interna opaca; nunca deriva de datos de presentación."""

    return str(uuid4())


def internal_id(value, field):
    """Valida un UUID interno de Oriva conservando su representación canónica."""

    if not isinstance(value, str):
        raise DomainValidationError(f"{field} debe ser un UUID interno de Oriva.")
    try:
        identifier = UUID(value.strip())
    except (AttributeError, ValueError) as error:
        raise DomainValidationError(
            f"{field} debe ser un UUID interno de Oriva; no use un ID externo."
        ) from error
    if str(identifier) != value.strip().lower():
        raise DomainValidationError(f"{field} debe usar el formato UUID canónico.")
    return str(identifier)


__all__ = ["internal_id", "new_internal_id"]
