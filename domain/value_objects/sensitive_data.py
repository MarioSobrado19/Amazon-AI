from domain.value_objects.frozen_mapping import FrozenMapping


_SENSITIVE_FRAGMENTS = (
    "email", "password", "secret", "token", "credential", "apikey",
    "authorization", "bearer",
)


def _normalized_key(value):
    return "".join(character for character in value.lower() if character.isalnum())


def contains_sensitive_key(value):
    if isinstance(value, FrozenMapping):
        return any(
            any(fragment in _normalized_key(key) for fragment in _SENSITIVE_FRAGMENTS)
            or contains_sensitive_key(nested)
            for key, nested in value.items
        )
    if isinstance(value, tuple):
        return any(contains_sensitive_key(item) for item in value)
    return False


def contains_sensitive_reference(value):
    """Detecta marcadores de secretos en referencias externas sin guardar valores."""
    if value is None:
        return False
    normalized = value.lower().replace("-", "_")
    markers = (
        "access_token", "refresh_token", "authorization", "bearer ",
        "client_secret", "api_key", "apikey", "password=", "credential",
    )
    return any(marker in normalized for marker in markers)
