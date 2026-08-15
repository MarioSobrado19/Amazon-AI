"""Adquiere las tarifas base de planes de venta desde la página oficial de Amazon US."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
import socket
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID, uuid5

from application.research_models import (
    ResearchCapabilityRequest,
    ResearchCapabilityResult,
    ResearchCapabilityResultStatus,
    ResearchFailure,
)
from domain.entities import EvidenceRecord
from domain.enums import (
    ConfidenceLevel,
    EvidenceType,
    FreshnessStatus,
    ResearchCategory,
    VerificationStatus,
)


SOURCE_URL = "https://sell.amazon.com/pricing?mons_sel_locale=en_US"
CAPABILITY_ID = "amazon-us-marketplace-conditions-v1"
MARKETPLACE_ID = "amazon-us"
_EVIDENCE_NAMESPACE = UUID("b9c39fa0-f48d-48b2-a00b-da85932f428e")
_ALLOWED_HOST = "sell.amazon.com"
_MAX_RESPONSE_BYTES = 2_000_000


class SourceAcquisitionError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class SourceDocument:
    body: str
    final_url: str
    retrieved_at: datetime
    content_type: str = "text/html"


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.hidden_depth and data.strip():
            self.parts.append(data.strip())


def _official_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == _ALLOWED_HOST
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
    )


class _OfficialRedirectHandler(HTTPRedirectHandler):
    """Impide descargar contenido desde un destino fuera del allowlist."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _official_https_url(newurl):
            raise SourceAcquisitionError(
                "unexpected_redirect",
                "La fuente intentó redirigir fuera del dominio oficial permitido.",
                retryable=False,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_official_pricing_page(*, timeout_seconds: float = 10.0) -> SourceDocument:
    """Descarga únicamente la URL oficial allowlisted, con límites explícitos."""
    request = Request(
        SOURCE_URL,
        headers={"User-Agent": "Oriva/1.0 marketplace-conditions-research"},
    )
    try:
        with build_opener(_OfficialRedirectHandler()).open(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            if not _official_https_url(final_url):
                raise SourceAcquisitionError(
                    "unexpected_redirect", "La fuente redirigió fuera del dominio oficial permitido.", retryable=False,
                )
            content_type = response.headers.get_content_type()
            if content_type != "text/html":
                raise SourceAcquisitionError(
                    "unexpected_content_type", "La fuente oficial no devolvió HTML.", retryable=True,
                )
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise SourceAcquisitionError(
                    "response_too_large", "La respuesta oficial excede el límite permitido.", retryable=False,
                )
            charset = response.headers.get_content_charset() or "utf-8"
            return SourceDocument(raw.decode(charset), final_url, datetime.now(timezone.utc), content_type)
    except SourceAcquisitionError:
        raise
    except (TimeoutError, socket.timeout) as error:
        raise SourceAcquisitionError("timeout", "La fuente oficial no respondió a tiempo.", retryable=True) from error
    except HTTPError as error:
        retryable = error.code == 429 or error.code >= 500
        raise SourceAcquisitionError("http_error", f"La fuente oficial respondió con HTTP {error.code}.", retryable=retryable) from error
    except (URLError, UnicodeError) as error:
        raise SourceAcquisitionError("source_unavailable", "No se pudo leer la fuente oficial.", retryable=True) from error


def _visible_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def parse_selling_plan_fees(html: str) -> dict:
    """Extrae solo los dos importes publicados; falla cerrado si el formato cambia."""
    text = _visible_text(html)
    if not text or re.search(r"\b(?:access denied|temporarily unavailable|error page|service unavailable)\b", text, re.IGNORECASE):
        raise SourceAcquisitionError(
            "source_format_changed",
            "La página oficial no contiene el formato verificable esperado para ambos planes.",
            retryable=False,
        )
    amount = r"([0-9]+(?:\.[0-9]{2})?)"
    individual = re.findall(rf"\bIndividual\b\s+\$\s*{amount}\s*/?\s*(?:item sold|per item sold)\b", text, re.IGNORECASE)
    professional = re.findall(rf"\bProfessional\b\s+\$\s*{amount}\s*/?\s*(?:per\s+)?month\b", text, re.IGNORECASE)
    if len(individual) != 1 or len(professional) != 1:
        raise SourceAcquisitionError(
            "source_format_changed",
            "La página oficial no contiene una única tarifa USD verificable para cada plan.",
            retryable=False,
        )
    return {
        "condition_type": "selling_plan_base_fees",
        "currency": "USD",
        "individual": {"amount": individual[0], "billing_basis": "per_item_sold"},
        "professional": {"amount": professional[0], "billing_basis": "per_month"},
    }


class AmazonUSMarketplaceConditionsCapability:
    capability_id = CAPABILITY_ID
    supported_categories = (ResearchCategory.MARKETPLACE,)
    supported_regions = ("US",)
    supported_subject_types = ("business_path", "marketplace")

    def __init__(self, fetcher: Callable[[], SourceDocument] = fetch_official_pricing_page):
        self._fetcher = fetcher

    def can_handle(self, request: ResearchCapabilityRequest) -> bool:
        return (
            isinstance(request, ResearchCapabilityRequest)
            and request.category is ResearchCategory.MARKETPLACE
            and request.subject_type in self.supported_subject_types
            and request.region is not None
            and request.region.country_code == "US"
            and request.marketplace_id == MARKETPLACE_ID
        )

    def execute(self, request: ResearchCapabilityRequest) -> ResearchCapabilityResult:
        now = datetime.now(timezone.utc)
        if not self.can_handle(request):
            failure = ResearchFailure(
                "unsupported_request", "La capability solo admite condiciones públicas de Amazon US.",
                False, self.capability_id, now,
            )
            return ResearchCapabilityResult(
                request.task_id, ResearchCapabilityResultStatus.FAILED,
                self.capability_id, now, failure=failure,
            )
        try:
            document = self._fetcher()
            if not _official_https_url(document.final_url):
                raise SourceAcquisitionError(
                    "untrusted_source", "El documento no procede del dominio oficial permitido.", retryable=False,
                )
            values = parse_selling_plan_fees(document.body)
            canonical_values = json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            digest = sha256(canonical_values.encode("utf-8")).hexdigest()
            identity = "|".join((request.task_id, document.final_url, document.retrieved_at.isoformat(), digest))
            evidence = EvidenceRecord(
                str(uuid5(_EVIDENCE_NAMESPACE, identity)),
                request.subject_type,
                request.subject_id,
                ResearchCategory.MARKETPLACE,
                EvidenceType.DATA,
                {**values, "content_sha256": digest},
                "Amazon Sell official pricing page",
                document.retrieved_at,
                document.retrieved_at,
                FreshnessStatus.CURRENT,
                VerificationStatus.VERIFIED,
                ConfidenceLevel.HIGH,
                "amazon-us-marketplace-conditions/1.0",
                source_reference=document.final_url,
                region=request.region,
                marketplace_id=MARKETPLACE_ID,
                limitations=(
                    "Solo cubre las tarifas base de los planes Individual y Professional.",
                    "No incluye tarifas por referencia, FBA, almacenamiento, publicidad, impuestos ni promociones.",
                    "La fuente no declara una fecha efectiva estructurada; observed_at corresponde a la consulta.",
                    "content_sha256 identifica los valores normalizados cubiertos, no el HTML completo.",
                ),
            )
            return ResearchCapabilityResult(
                request.task_id, ResearchCapabilityResultStatus.SUCCESS,
                self.capability_id, document.retrieved_at, (evidence,),
                warnings=("Las tarifas adicionales permanecen fuera del alcance de Marketplace Conditions V1.",),
                capability_version="1.0",
            )
        except SourceAcquisitionError as error:
            failed_at = datetime.now(timezone.utc)
            failure = ResearchFailure(
                error.code, str(error), error.retryable, self.capability_id, failed_at,
                {"source_host": _ALLOWED_HOST},
            )
            return ResearchCapabilityResult(
                request.task_id, ResearchCapabilityResultStatus.FAILED,
                self.capability_id, failed_at, failure=failure, capability_version="1.0",
            )
