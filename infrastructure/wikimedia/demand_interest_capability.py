"""Adquiere vistas diarias de un artículo desde Wikimedia Analytics API."""

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from hashlib import sha256
import json
import re
import socket
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
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


CAPABILITY_ID = "wikimedia-pageviews-demand-interest-v1"
CAPABILITY_VERSION = "1.0"
PARSER_VERSION = "wikimedia-pageviews/1.0"
PROJECT = "en.wikipedia.org"
RESPONSE_PROJECT = "en.wikipedia"
_API_ROOT = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
_ALLOWED_HOST = "wikimedia.org"
_MAX_RESPONSE_BYTES = 1_000_000
_USER_AGENT = "Oriva/1.0 (https://github.com/MarioSobrado19/Amazon-AI)"
_EVIDENCE_NAMESPACE = UUID("21a7ad40-f55c-4d45-8a23-a410249738df")


class SourceAcquisitionError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class SourceNoData(Exception):
    """La fuente respondió válidamente pero no publicó observaciones."""


@dataclass(frozen=True, slots=True)
class SourceDocument:
    body: str
    final_url: str
    retrieved_at: datetime
    content_type: str = "application/json"


def _official_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == _ALLOWED_HOST
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
        and parsed.path.startswith("/api/rest_v1/metrics/pageviews/per-article/")
    )


class _OfficialRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _official_https_url(newurl):
            raise SourceAcquisitionError(
                "unexpected_redirect",
                "La fuente intentó redirigir fuera del endpoint oficial permitido.",
                retryable=False,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def parse_time_scope(value: str | None) -> tuple[date, date]:
    """Acepta exclusivamente YYYY-MM-DD/YYYY-MM-DD, sin fechas futuras."""
    if not value or not re.fullmatch(r"\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}", value):
        raise SourceAcquisitionError(
            "invalid_time_scope",
            "time_scope debe usar YYYY-MM-DD/YYYY-MM-DD.",
            retryable=False,
        )
    try:
        start, end = (date.fromisoformat(part) for part in value.split("/"))
    except ValueError as error:
        raise SourceAcquisitionError(
            "invalid_time_scope",
            "time_scope contiene una fecha inválida.",
            retryable=False,
        ) from error
    if end < start or (end - start).days > 366:
        raise SourceAcquisitionError(
            "invalid_time_scope",
            "El intervalo debe estar ordenado y no exceder 367 días inclusivos.",
            retryable=False,
        )
    if end >= datetime.now(timezone.utc).date():
        raise SourceAcquisitionError(
            "incomplete_time_scope",
            "El intervalo debe terminar antes del día UTC actual.",
            retryable=False,
        )
    return start, end


def build_source_url(article_title: str, start: date, end: date) -> str:
    title = quote(article_title.replace(" ", "_"), safe="()_-.~")
    return (
        f"{_API_ROOT}/{PROJECT}/all-access/user/{title}/daily/"
        f"{start:%Y%m%d}/{end:%Y%m%d}"
    )


def fetch_official_pageviews(
    article_title: str, start: date, end: date, *, timeout_seconds: float = 10.0,
) -> SourceDocument:
    source_url = build_source_url(article_title, start, end)
    request = Request(
        source_url,
        headers={
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
    )
    try:
        with build_opener(_OfficialRedirectHandler()).open(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            if not _official_https_url(final_url):
                raise SourceAcquisitionError(
                    "unexpected_redirect",
                    "La fuente redirigió fuera del endpoint oficial permitido.",
                    retryable=False,
                )
            content_type = response.headers.get_content_type()
            if content_type != "application/json":
                raise SourceAcquisitionError(
                    "unexpected_content_type",
                    "La fuente oficial no devolvió JSON.",
                    retryable=True,
                )
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise SourceAcquisitionError(
                    "response_too_large",
                    "La respuesta oficial excede el límite permitido.",
                    retryable=False,
                )
            charset = response.headers.get_content_charset() or "utf-8"
            return SourceDocument(raw.decode(charset), final_url, datetime.now(timezone.utc), content_type)
    except SourceAcquisitionError:
        raise
    except HTTPError as error:
        if error.code == 404:
            raise SourceNoData("La fuente oficial no publicó observaciones para el artículo y periodo.") from error
        retryable = error.code == 429 or error.code >= 500
        raise SourceAcquisitionError(
            "http_error", f"La fuente oficial respondió con HTTP {error.code}.", retryable=retryable,
        ) from error
    except (TimeoutError, socket.timeout) as error:
        raise SourceAcquisitionError(
            "timeout", "La fuente oficial no respondió a tiempo.", retryable=True,
        ) from error
    except (URLError, UnicodeError) as error:
        raise SourceAcquisitionError(
            "source_unavailable", "No se pudo leer la fuente oficial.", retryable=True,
        ) from error


def parse_pageviews(body: str, article_title: str, start: date, end: date) -> dict:
    """Valida la serie exacta; no rellena días ni adivina observaciones."""
    try:
        payload = json.loads(body)
    except (TypeError, json.JSONDecodeError) as error:
        raise SourceAcquisitionError(
            "source_format_changed", "La respuesta oficial no contiene JSON válido.", retryable=False,
        ) from error
    if not isinstance(payload, dict) or set(payload) != {"items"} or not isinstance(payload["items"], list):
        raise SourceAcquisitionError(
            "source_format_changed", "La respuesta oficial no contiene la estructura esperada.", retryable=False,
        )
    if not payload["items"]:
        raise SourceNoData("La fuente oficial respondió sin observaciones para el periodo.")

    expected_dates = []
    cursor = start
    while cursor <= end:
        expected_dates.append(cursor)
        cursor = date.fromordinal(cursor.toordinal() + 1)
    observations = []
    seen = set()
    expected_article = article_title.replace(" ", "_")
    required_keys = {"project", "article", "granularity", "timestamp", "access", "agent", "views"}
    for item in payload["items"]:
        if not isinstance(item, dict) or set(item) != required_keys:
            raise SourceAcquisitionError(
                "source_format_changed", "Una observación oficial tiene campos inesperados o incompletos.", retryable=False,
            )
        if (
            item["project"] != RESPONSE_PROJECT
            or item["article"] != expected_article
            or item["granularity"] != "daily"
            or item["access"] != "all-access"
            or item["agent"] != "user"
            or not isinstance(item["views"], int)
            or isinstance(item["views"], bool)
            or item["views"] < 0
        ):
            raise SourceAcquisitionError(
                "ambiguous_source_data", "Una observación no coincide con la consulta exacta solicitada.", retryable=False,
            )
        try:
            observed_date = datetime.strptime(item["timestamp"], "%Y%m%d00").date()
        except (TypeError, ValueError) as error:
            raise SourceAcquisitionError(
                "source_format_changed", "Una observación contiene un timestamp inválido.", retryable=False,
            ) from error
        if observed_date in seen:
            raise SourceAcquisitionError(
                "ambiguous_source_data", "La fuente devolvió fechas duplicadas.", retryable=False,
            )
        seen.add(observed_date)
        observations.append({"date": observed_date.isoformat(), "views": item["views"]})
    if sorted(seen) != expected_dates:
        raise SourceAcquisitionError(
            "incomplete_source_data", "La serie oficial no cubre exactamente todos los días solicitados.", retryable=False,
        )
    observations.sort(key=lambda item: item["date"])
    return {
        "signal_type": "wikipedia_article_pageviews",
        "metric": "page_views",
        "project": PROJECT,
        "response_project": RESPONSE_PROJECT,
        "article_title": article_title,
        "access": "all-access",
        "agent": "user",
        "granularity": "daily",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "observations": observations,
        "total_views": sum(item["views"] for item in observations),
    }


class WikimediaPageviewsDemandCapability:
    capability_id = CAPABILITY_ID
    supported_categories = (ResearchCategory.DEMAND,)
    supported_regions = None
    supported_subject_types = ("wikipedia_article",)

    def __init__(self, fetcher: Callable[[str, date, date], SourceDocument] = fetch_official_pageviews):
        self._fetcher = fetcher

    def can_handle(self, request: ResearchCapabilityRequest) -> bool:
        question = request.question.casefold()
        attention_question = (
            "wikipedia" in question
            and any(term in question for term in ("artículo", "articulo", "article"))
            and any(term in question for term in ("vista", "pageview", "atención", "atencion", "lectura"))
        )
        commercial_question = any(
            term in question
            for term in (
                "unidad", "venta", "conversión", "conversion", "demanda suficiente",
                "demanda comercial", "amazon", "walmart", "ebay", "etsy", "tiktok shop",
            )
        )
        return (
            isinstance(request, ResearchCapabilityRequest)
            and request.category is ResearchCategory.DEMAND
            and request.subject_type in self.supported_subject_types
            and request.region is None
            and request.marketplace_id is None
            and bool(request.time_scope)
            and attention_question
            and not commercial_question
        )

    def execute(self, request: ResearchCapabilityRequest) -> ResearchCapabilityResult:
        now = datetime.now(timezone.utc)
        if not self.can_handle(request):
            failure = ResearchFailure(
                "unsupported_request",
                "La capability solo admite interés global por artículo, sin región ni marketplace.",
                False,
                self.capability_id,
                now,
            )
            return ResearchCapabilityResult(
                request.task_id, ResearchCapabilityResultStatus.FAILED,
                self.capability_id, now, failure=failure, capability_version=CAPABILITY_VERSION,
            )
        try:
            start, end = parse_time_scope(request.time_scope)
            document = self._fetcher(request.subject_id, start, end)
            if not _official_https_url(document.final_url):
                raise SourceAcquisitionError(
                    "untrusted_source", "El documento no procede del endpoint oficial permitido.", retryable=False,
                )
            values = parse_pageviews(document.body, request.subject_id, start, end)
            canonical = json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            digest = sha256(canonical.encode("utf-8")).hexdigest()
            identity = "|".join((request.task_id, document.final_url, document.retrieved_at.isoformat(), digest))
            observed_at = datetime.combine(end, time(23, 59, 59), tzinfo=timezone.utc)
            evidence = EvidenceRecord(
                str(uuid5(_EVIDENCE_NAMESPACE, identity)),
                request.subject_type,
                request.subject_id,
                ResearchCategory.DEMAND,
                EvidenceType.DATA,
                {**values, "semantic_sha256": digest, "geographic_scope": "not_geolocated"},
                "Wikimedia Analytics API",
                observed_at,
                document.retrieved_at,
                FreshnessStatus.CURRENT,
                VerificationStatus.VERIFIED,
                ConfidenceLevel.HIGH,
                PARSER_VERSION,
                source_reference=document.final_url,
                valid_from=datetime.combine(start, time.min, tzinfo=timezone.utc),
                valid_until=observed_at,
                region=None,
                marketplace_id=None,
                limitations=(
                    "Mide solicitudes de contenido clasificadas por Wikimedia como page views del artículo indicado.",
                    "No mide búsquedas, ventas, unidades, ingresos, intención de compra, conversión ni tamaño de mercado.",
                    "La señal no está geolocalizada y la edición lingüística no equivale a una región comercial.",
                    "Títulos alternativos, redirects, ambigüedad del concepto y eventos externos pueden cambiar las vistas.",
                    "El filtro agent=user reduce tráfico clasificado como spider/automated, pero no identifica personas únicas.",
                    "semantic_sha256 cubre la serie normalizada y sus parámetros, no el JSON visual completo.",
                    "El título del artículo fue suministrado explícitamente; V1 no resuelve ni confirma su equivalencia con un producto comercial.",
                ),
            )
            return ResearchCapabilityResult(
                request.task_id,
                ResearchCapabilityResultStatus.SUCCESS,
                self.capability_id,
                document.retrieved_at,
                (evidence,),
                warnings=("Las page views son una señal de atención y no evidencia de ventas.",),
                capability_version=CAPABILITY_VERSION,
            )
        except SourceNoData:
            completed_at = datetime.now(timezone.utc)
            return ResearchCapabilityResult(
                request.task_id,
                ResearchCapabilityResultStatus.NO_DATA,
                self.capability_id,
                completed_at,
                missing_information=("No hubo observaciones oficiales verificables para el artículo y periodo solicitados.",),
                warnings=("NO_DATA no afirma ausencia de demanda ni de ventas.",),
                capability_version=CAPABILITY_VERSION,
            )
        except SourceAcquisitionError as error:
            failed_at = datetime.now(timezone.utc)
            failure = ResearchFailure(
                error.code,
                str(error),
                error.retryable,
                self.capability_id,
                failed_at,
                {"source_host": _ALLOWED_HOST, "project": PROJECT},
            )
            return ResearchCapabilityResult(
                request.task_id,
                ResearchCapabilityResultStatus.FAILED,
                self.capability_id,
                failed_at,
                failure=failure,
                capability_version=CAPABILITY_VERSION,
            )
