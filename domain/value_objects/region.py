from dataclasses import dataclass

from domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class Region:
    """Ámbito territorial inmutable, sin asumir un marketplace concreto."""

    country_code: str
    area: str | None = None

    def __post_init__(self):
        if not isinstance(self.country_code, str):
            raise DomainValidationError("country_code debe ser un código de dos letras.")
        country_code = self.country_code.strip().upper()
        if len(country_code) != 2 or not country_code.isalpha():
            raise DomainValidationError("country_code debe ser un código de dos letras.")
        object.__setattr__(self, "country_code", country_code)
        if self.area is None:
            area = None
        elif not isinstance(self.area, str) or not self.area.strip():
            raise DomainValidationError("area debe ser texto no vacío.")
        else:
            area = self.area.strip()
        object.__setattr__(self, "area", area)

    def to_dict(self):
        return {"country_code": self.country_code, "area": self.area}
