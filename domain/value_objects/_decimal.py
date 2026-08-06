from decimal import Decimal, InvalidOperation

from domain.exceptions import DomainValidationError


def validated_decimal(value, field):
    """Convierte números finitos a Decimal sin aceptar booleanos."""
    if isinstance(value, bool):
        raise DomainValidationError(f"{field} debe ser un número finito.")
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise DomainValidationError(
            f"{field} debe ser un número finito."
        ) from error
    if not decimal_value.is_finite():
        raise DomainValidationError(f"{field} debe ser un número finito.")
    return decimal_value

