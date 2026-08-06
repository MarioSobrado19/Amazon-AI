from domain.exceptions import DomainValidationError


def required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise DomainValidationError(f"{field} es obligatorio.")
    return value.strip()


def optional_text(value, field):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise DomainValidationError(f"{field} debe ser texto no vacío.")
    return value.strip()

