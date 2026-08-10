from datetime import datetime
from decimal import Decimal

from domain.entities._validation import optional_text, required_text
from domain.enums import InformationSource
from domain.exceptions import DomainValidationError
from domain.value_objects._decimal import validated_decimal


def declared_source(value, field="source"):
    if not isinstance(value, InformationSource):
        raise DomainValidationError(f"{field} debe ser una procedencia válida.")
    if value is not InformationSource.USER_DECLARED:
        raise DomainValidationError(
            f"{field} solo puede ser información declarada por el usuario en esta versión."
        )
    return value


def optional_non_negative_decimal(value, field):
    if value is None:
        return None
    number = validated_decimal(value, field)
    if number < 0:
        raise DomainValidationError(f"{field} debe ser no negativo.")
    return number


def optional_scalar(value, field):
    if value is None or isinstance(value, (str, bool)):
        if isinstance(value, str):
            return required_text(value, field)
        return value
    if isinstance(value, (int, float, Decimal)):
        return validated_decimal(value, field)
    raise DomainValidationError(
        f"{field} debe ser texto, booleano, número finito o None."
    )


def aware_datetime(value, field):
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise DomainValidationError(f"{field} debe incluir zona horaria.")
    if value.utcoffset() is None:
        raise DomainValidationError(f"{field} debe incluir zona horaria válida.")
    return value


def serialize_scalar(value):
    return str(value) if isinstance(value, Decimal) else value


__all__ = [
    "aware_datetime",
    "declared_source",
    "optional_non_negative_decimal",
    "optional_scalar",
    "optional_text",
    "required_text",
    "serialize_scalar",
]
