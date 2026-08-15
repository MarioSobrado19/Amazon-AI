"""Capability configurable y completamente in-memory para pruebas."""

from datetime import datetime, timezone
from uuid import uuid4

from application.research_models import (
    ResearchCapabilityResult, ResearchCapabilityResultStatus, ResearchFailure,
)
from domain.entities import EvidenceRecord
from domain.enums import ConfidenceLevel, EvidenceType, FreshnessStatus, VerificationStatus


class FakeResearchCapability:
    def __init__(self, capability_id, categories, *, subject_types=("business_path",),
                 region_codes=None, mode="success", evidence_factory=None):
        self.capability_id = capability_id
        self.supported_categories = tuple(categories)
        self.supported_subject_types = tuple(subject_types)
        self.supported_regions = tuple(region_codes) if region_codes is not None else None
        self.mode = mode
        self.evidence_factory = evidence_factory

    def can_handle(self, request):
        region_ok = self.supported_regions is None or (
            request.region is not None and request.region.country_code in self.supported_regions
        )
        return request.category in self.supported_categories and request.subject_type in self.supported_subject_types and region_ok

    def _evidence(self, request, now):
        if self.evidence_factory:
            return self.evidence_factory(request, now)
        return EvidenceRecord(
            str(uuid4()), request.subject_type, request.subject_id, request.category,
            EvidenceType.DATA, {"observed": True}, f"fake:{self.capability_id}",
            now, now, FreshnessStatus.CURRENT, VerificationStatus.VERIFIED,
            ConfidenceLevel.MEDIUM, "fake/1", region=request.region,
            marketplace_id=request.marketplace_id,
            limitations=("Evidencia simulada exclusivamente para pruebas.",),
        )

    def execute(self, request):
        now = datetime.now(timezone.utc)
        if self.mode in ("timeout", "unavailable", "recoverable_failure", "fatal_failure"):
            retryable = self.mode != "fatal_failure"
            failure = ResearchFailure(self.mode, "Fallo técnico simulado.", retryable, self.capability_id, now, {"mode": self.mode})
            return ResearchCapabilityResult(request.task_id, ResearchCapabilityResultStatus.FAILED, self.capability_id, now, failure=failure)
        if self.mode == "no_data":
            return ResearchCapabilityResult(request.task_id, ResearchCapabilityResultStatus.NO_DATA, self.capability_id, now, missing_information=("La capability no obtuvo evidencia suficiente.",))
        item = self._evidence(request, now)
        if self.mode == "partial":
            return ResearchCapabilityResult(request.task_id, ResearchCapabilityResultStatus.PARTIAL, self.capability_id, now, (item,), ("Falta corroboración adicional.",))
        return ResearchCapabilityResult(request.task_id, ResearchCapabilityResultStatus.SUCCESS, self.capability_id, now, (item,))
