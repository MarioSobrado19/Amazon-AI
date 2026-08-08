from datetime import datetime

from domain.entities._validation import optional_text, required_text
from domain.exceptions import DomainValidationError


def text_tuple(values, field):
    try:
        values = tuple(values)
    except TypeError as error:
        raise DomainValidationError(f"{field} debe ser una colección de textos.") from error
    return tuple(required_text(value, field) for value in values)


def aware_datetime(value, field):
    if not isinstance(value, datetime):
        raise DomainValidationError(f"{field} debe ser una fecha válida.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise DomainValidationError(f"{field} debe incluir zona horaria.")
    return value


def optional_aware_datetime(value, field):
    if value is None:
        return None
    return aware_datetime(value, field)


def valid_period(valid_from, valid_until):
    valid_from = optional_aware_datetime(valid_from, "valid_from")
    valid_until = optional_aware_datetime(valid_until, "valid_until")
    if valid_from is not None and valid_until is not None and valid_until < valid_from:
        raise DomainValidationError("valid_until no puede ser anterior a valid_from.")
    return valid_from, valid_until


def currency_code(value):
    if not isinstance(value, str):
        raise DomainValidationError("currency debe ser un código de tres letras.")
    value = value.strip().upper()
    if len(value) != 3 or not value.isalpha():
        raise DomainValidationError("currency debe ser un código de tres letras.")
    return value


__all__ = [
    "aware_datetime",
    "currency_code",
    "optional_aware_datetime",
    "optional_text",
    "required_text",
    "text_tuple",
    "valid_period",
]

