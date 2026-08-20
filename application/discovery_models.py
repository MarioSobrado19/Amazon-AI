"""Contratos efímeros para discovery anterior a Opportunity.

INTERNAL / CONFIDENTIAL — ORIVA. Estos contratos no autorizan ejecución,
inversión ni promoción automática a entidades comerciales posteriores.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import unicodedata
from uuid import UUID, uuid5

from domain.entities import EvidenceRecord
from domain.entities._marketplace_validation import aware_datetime, optional_text, required_text, text_tuple
from domain.enums import FreshnessStatus, VerificationStatus
from domain.exceptions import DomainValidationError
from domain.value_objects import FrozenMapping, Region, ResearchNeed


_SIGNAL_NAMESPACE = UUID("58db069a-2027-4bb7-aac7-760c67d29531")
_HYPOTHESIS_NAMESPACE = UUID("dbb41e0e-08ca-4c66-bae3-aa8f93a1a04b")


class DiscoverySignalType(str, Enum):
    ATTENTION = "attention"
    SEARCH_INTEREST = "search_interest"
    CATALOG_PRESENCE = "catalog_presence"
    COMMERCIAL_LISTING_PRESENCE = "commercial_listing_presence"
    PRICE_OBSERVATION = "price_observation"
    CATEGORY_ACTIVITY = "category_activity"
    MARKETPLACE_PRESENCE = "marketplace_presence"
    SUPPLY_SIGNAL = "supply_signal"
    MACRO_CONSUMER_SIGNAL = "macro_consumer_signal"
    TREND_CHANGE = "trend_change"


class DiscoverySourceKind(str, Enum):
    REAL = "real"
    SANDBOX = "sandbox"
    FIXTURE = "fixture"
    SIMULATION = "simulation"


class HypothesisIdentityKind(str, Enum):
    PRODUCT = "product"
    CONCEPT = "concept"
    CATEGORY = "category"
    KEYWORD = "keyword"


class OpportunityHypothesisState(str, Enum):
    SURFACED = "surfaced"
    RESEARCH_READY = "research_ready"
    STALE = "stale"
    CONTRADICTED = "contradicted"
    EXCLUDED = "excluded"


class DiscoverySourceStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    NO_DATA = "no_data"
    TECHNICAL_FAILURE = "technical_failure"


class DiscoveryRunStatus(str, Enum):
    HYPOTHESES_IDENTIFIED = "hypotheses_identified"
    HOLD_EVIDENCE_ACQUISITION = "hold_evidence_acquisition"
    PARTIAL = "partial"
    NO_DATA = "no_data"
    TECHNICAL_FAILURE = "technical_failure"


def normalize_identity(value: str) -> str:
    value = required_text(value, "identity_value")
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class DiscoverySignal:
    signal_type: DiscoverySignalType
    identity_kind: HypothesisIdentityKind
    identity_value: str
    source: str
    source_kind: DiscoverySourceKind
    observed_at: datetime
    retrieved_at: datetime
    freshness: FreshnessStatus
    verification_status: VerificationStatus
    method_version: str
    value: FrozenMapping = FrozenMapping()
    source_reference: str | None = None
    region: Region | None = None
    marketplace_id: str | None = None
    evidence_record: EvidenceRecord | None = None
    limitations: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    signal_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.signal_type, DiscoverySignalType):
            raise DomainValidationError("signal_type debe ser válido.")
        if not isinstance(self.identity_kind, HypothesisIdentityKind):
            raise DomainValidationError("identity_kind debe ser válido.")
        if not isinstance(self.source_kind, DiscoverySourceKind):
            raise DomainValidationError("source_kind debe ser válido.")
        object.__setattr__(self, "identity_value", required_text(self.identity_value, "identity_value"))
        object.__setattr__(self, "source", required_text(self.source, "source"))
        object.__setattr__(self, "method_version", required_text(self.method_version, "method_version"))
        object.__setattr__(self, "source_reference", optional_text(self.source_reference, "source_reference"))
        object.__setattr__(self, "marketplace_id", optional_text(self.marketplace_id, "marketplace_id"))
        object.__setattr__(self, "observed_at", aware_datetime(self.observed_at, "observed_at"))
        object.__setattr__(self, "retrieved_at", aware_datetime(self.retrieved_at, "retrieved_at"))
        if self.retrieved_at < self.observed_at:
            raise DomainValidationError("retrieved_at no puede preceder observed_at.")
        if not isinstance(self.freshness, FreshnessStatus) or not isinstance(self.verification_status, VerificationStatus):
            raise DomainValidationError("freshness y verification_status deben ser válidos.")
        if self.region is not None and not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser Region.")
        if self.evidence_record is not None and not isinstance(self.evidence_record, EvidenceRecord):
            raise DomainValidationError("evidence_record debe ser EvidenceRecord.")
        value = self.value if isinstance(self.value, FrozenMapping) else FrozenMapping.from_mapping(self.value)
        object.__setattr__(self, "value", value)
        for field in ("limitations", "contradictions"):
            object.__setattr__(self, field, tuple(sorted(set(text_tuple(getattr(self, field), field)))))
        semantic = {
            "type": self.signal_type.value,
            "identity": [self.identity_kind.value, normalize_identity(self.identity_value)],
            "source": self.source,
            "source_kind": self.source_kind.value,
            "source_reference": self.source_reference,
            "observed_at": self.observed_at.isoformat(),
            "region": self.region.to_dict() if self.region else None,
            "marketplace": self.marketplace_id,
            "method_version": self.method_version,
            "value": value.to_dict(),
        }
        expected = str(uuid5(_SIGNAL_NAMESPACE, _canonical(semantic)))
        if self.signal_id is not None and self.signal_id != expected:
            raise DomainValidationError("signal_id no coincide con la señal semántica.")
        object.__setattr__(self, "signal_id", expected)

    @property
    def is_real(self) -> bool:
        return self.source_kind is DiscoverySourceKind.REAL

    def to_dict(self):
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type.value,
            "identity_kind": self.identity_kind.value,
            "identity_value": self.identity_value,
            "source": self.source,
            "source_kind": self.source_kind.value,
            "source_reference": self.source_reference,
            "observed_at": self.observed_at.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat(),
            "freshness": self.freshness.value,
            "verification_status": self.verification_status.value,
            "method_version": self.method_version,
            "value": self.value.to_dict(),
            "region": self.region.to_dict() if self.region else None,
            "marketplace_id": self.marketplace_id,
            "evidence_id": self.evidence_record.evidence_id if self.evidence_record else None,
            "limitations": list(self.limitations),
            "contradictions": list(self.contradictions),
        }


@dataclass(frozen=True, slots=True)
class OpportunityHypothesis:
    identity_kind: HypothesisIdentityKind
    identity_value: str
    signals: tuple[DiscoverySignal, ...]
    research_needs: tuple[ResearchNeed, ...]
    observed_at: datetime
    freshness: FreshnessStatus
    verification_status: VerificationStatus
    state: OpportunityHypothesisState
    method_version: str
    why_surfaced: tuple[str, ...]
    unknowns: tuple[str, ...]
    contradictions: tuple[str, ...] = ()
    region: Region | None = None
    potential_marketplaces: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    hypothesis_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.identity_kind, HypothesisIdentityKind):
            raise DomainValidationError("identity_kind debe ser válido.")
        object.__setattr__(self, "identity_value", required_text(self.identity_value, "identity_value"))
        object.__setattr__(self, "method_version", required_text(self.method_version, "method_version"))
        signals = tuple(sorted(tuple(self.signals), key=lambda item: item.signal_id))
        if not signals or any(not isinstance(item, DiscoverySignal) for item in signals):
            raise DomainValidationError("signals debe contener señales válidas.")
        if len({item.signal_id for item in signals}) != len(signals):
            raise DomainValidationError("signals no puede contener duplicados.")
        object.__setattr__(self, "signals", signals)
        needs = tuple(sorted(tuple(self.research_needs), key=lambda item: item.need_id))
        if any(not isinstance(item, ResearchNeed) for item in needs):
            raise DomainValidationError("research_needs debe contener necesidades válidas.")
        object.__setattr__(self, "research_needs", needs)
        object.__setattr__(self, "observed_at", aware_datetime(self.observed_at, "observed_at"))
        if not isinstance(self.freshness, FreshnessStatus) or not isinstance(self.verification_status, VerificationStatus):
            raise DomainValidationError("freshness y verification_status deben ser válidos.")
        if not isinstance(self.state, OpportunityHypothesisState):
            raise DomainValidationError("state debe ser válido.")
        if self.region is not None and not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser Region.")
        for field in ("why_surfaced", "unknowns", "contradictions", "potential_marketplaces", "limitations"):
            object.__setattr__(self, field, tuple(sorted(set(text_tuple(getattr(self, field), field)))))
        semantic = {
            "identity": [self.identity_kind.value, normalize_identity(self.identity_value)],
            "region": self.region.to_dict() if self.region else None,
            "method_version": self.method_version,
        }
        expected = str(uuid5(_HYPOTHESIS_NAMESPACE, _canonical(semantic)))
        if self.hypothesis_id is not None and self.hypothesis_id != expected:
            raise DomainValidationError("hypothesis_id no coincide con la identidad semántica.")
        object.__setattr__(self, "hypothesis_id", expected)

    @property
    def evidence_records(self) -> tuple[EvidenceRecord, ...]:
        unique = {item.evidence_record.evidence_id: item.evidence_record for item in self.signals if item.evidence_record}
        return tuple(unique[key] for key in sorted(unique))

    @property
    def is_real(self) -> bool:
        return all(item.is_real for item in self.signals)

    def to_dict(self):
        return {
            "hypothesis_id": self.hypothesis_id,
            "identity_kind": self.identity_kind.value,
            "identity_value": self.identity_value,
            "region": self.region.to_dict() if self.region else None,
            "potential_marketplaces": list(self.potential_marketplaces),
            "originating_signal_ids": [item.signal_id for item in self.signals],
            "signals": [item.to_dict() for item in self.signals],
            "evidence_ids": [item.evidence_id for item in self.evidence_records],
            "source_provenance": sorted({item.source for item in self.signals}),
            "observed_at": self.observed_at.isoformat(),
            "freshness": self.freshness.value,
            "verification_status": self.verification_status.value,
            "state": self.state.value,
            "why_surfaced": list(self.why_surfaced),
            "limitations": list(self.limitations),
            "unknowns": list(self.unknowns),
            "contradictions": list(self.contradictions),
            "research_needs": [item.to_dict() for item in self.research_needs],
            "method_version": self.method_version,
            "is_real": self.is_real,
        }


@dataclass(frozen=True, slots=True)
class DiscoverySourceResult:
    source_id: str
    status: DiscoverySourceStatus
    generated_at: datetime
    signals: tuple[DiscoverySignal, ...] = ()
    missing_information: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    error_code: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "source_id", required_text(self.source_id, "source_id"))
        if not isinstance(self.status, DiscoverySourceStatus):
            raise DomainValidationError("status debe ser válido.")
        object.__setattr__(self, "generated_at", aware_datetime(self.generated_at, "generated_at"))
        signals = tuple(sorted(tuple(self.signals), key=lambda item: item.signal_id))
        if any(not isinstance(item, DiscoverySignal) for item in signals):
            raise DomainValidationError("signals contiene valores inválidos.")
        object.__setattr__(self, "signals", signals)
        for field in ("missing_information", "warnings"):
            object.__setattr__(self, field, tuple(sorted(set(text_tuple(getattr(self, field), field)))))
        object.__setattr__(self, "error_code", optional_text(self.error_code, "error_code"))
        if self.status is DiscoverySourceStatus.TECHNICAL_FAILURE and not self.error_code:
            raise DomainValidationError("technical_failure requiere error_code.")
        if self.status is DiscoverySourceStatus.NO_DATA and signals:
            raise DomainValidationError("no_data no puede incluir señales.")


@dataclass(frozen=True, slots=True)
class DiscoveryRequest:
    request_id: str
    objective_id: str
    generated_at: datetime
    region: Region | None = None
    future_capital_ceiling_usd: int | None = None
    currently_authorized_capital_usd: int = 0
    horizon_days: int | None = None
    max_hypotheses: int = 10

    def __post_init__(self):
        object.__setattr__(self, "request_id", required_text(self.request_id, "request_id"))
        object.__setattr__(self, "objective_id", required_text(self.objective_id, "objective_id"))
        object.__setattr__(self, "generated_at", aware_datetime(self.generated_at, "generated_at"))
        if self.region is not None and not isinstance(self.region, Region):
            raise DomainValidationError("region debe ser Region.")
        for field in ("future_capital_ceiling_usd", "horizon_days"):
            value = getattr(self, field)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise DomainValidationError(f"{field} debe ser entero no negativo o None.")
        if not isinstance(self.currently_authorized_capital_usd, int) or isinstance(self.currently_authorized_capital_usd, bool) or self.currently_authorized_capital_usd < 0:
            raise DomainValidationError("currently_authorized_capital_usd debe ser entero no negativo.")
        if not isinstance(self.max_hypotheses, int) or isinstance(self.max_hypotheses, bool) or not 1 <= self.max_hypotheses <= 10:
            raise DomainValidationError("max_hypotheses debe estar entre 1 y 10.")


@dataclass(frozen=True, slots=True)
class DiscoveryRunResult:
    request_id: str
    status: DiscoveryRunStatus
    hypotheses: tuple[OpportunityHypothesis, ...]
    source_results: tuple[DiscoverySourceResult, ...]
    generated_at: datetime
    missing_information: tuple[str, ...]
    warnings: tuple[str, ...]
    methodology_version: str

    def __post_init__(self):
        object.__setattr__(self, "request_id", required_text(self.request_id, "request_id"))
        if not isinstance(self.status, DiscoveryRunStatus):
            raise DomainValidationError("status debe ser válido.")
        hypotheses = tuple(sorted(tuple(self.hypotheses), key=lambda item: item.hypothesis_id))
        if any(not isinstance(item, OpportunityHypothesis) for item in hypotheses):
            raise DomainValidationError("hypotheses contiene valores inválidos.")
        object.__setattr__(self, "hypotheses", hypotheses)
        results = tuple(sorted(tuple(self.source_results), key=lambda item: item.source_id))
        if any(not isinstance(item, DiscoverySourceResult) for item in results):
            raise DomainValidationError("source_results contiene valores inválidos.")
        object.__setattr__(self, "source_results", results)
        object.__setattr__(self, "generated_at", aware_datetime(self.generated_at, "generated_at"))
        for field in ("missing_information", "warnings"):
            object.__setattr__(self, field, tuple(sorted(set(text_tuple(getattr(self, field), field)))))
        object.__setattr__(self, "methodology_version", required_text(self.methodology_version, "methodology_version"))

    @property
    def real_hypotheses(self):
        return tuple(item for item in self.hypotheses if item.is_real)

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "hypotheses": [item.to_dict() for item in self.hypotheses],
            "real_hypothesis_ids": [item.hypothesis_id for item in self.real_hypotheses],
            "source_results": [
                {"source_id": item.source_id, "status": item.status.value, "generated_at": item.generated_at.isoformat(), "signal_ids": [signal.signal_id for signal in item.signals], "missing_information": list(item.missing_information), "warnings": list(item.warnings), "error_code": item.error_code}
                for item in self.source_results
            ],
            "generated_at": self.generated_at.isoformat(),
            "missing_information": list(self.missing_information),
            "warnings": list(self.warnings),
            "methodology_version": self.methodology_version,
        }
