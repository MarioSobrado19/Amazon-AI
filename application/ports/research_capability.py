"""Puerto genérico para capacidades futuras de investigación."""

from typing import Protocol, runtime_checkable

from application.research_models import ResearchCapabilityRequest, ResearchCapabilityResult
from domain.enums import ResearchCategory


@runtime_checkable
class ResearchCapability(Protocol):
    capability_id: str
    supported_categories: tuple[ResearchCategory, ...]
    supported_regions: tuple[str, ...] | None
    supported_subject_types: tuple[str, ...]

    def can_handle(self, request: ResearchCapabilityRequest) -> bool: ...

    def execute(self, request: ResearchCapabilityRequest) -> ResearchCapabilityResult: ...
