"""Experimento de presencia documental con la API JSON de Library of Congress.

Este probe no implementa ResearchCapability, no produce EvidenceRecord y no
participa en ResearchAssessment. Conserva una fotografía de registros devueltos
por una consulta explícita, sin resolver entidades ni medir competencia.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import socket
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID, uuid5

from domain.value_objects import FrozenMapping


PROBE_ID = "loc-documentary-presence-experiment-v1"
PROBE_VERSION = "1.0"
PARSER_VERSION = "loc-json-books-collection-search/1.0"
SOURCE_NAME = "Library of Congress JSON API"
_SOURCE_ROOT = "https://www.loc.gov/books/"
_ALLOWED_HOST = "www.loc.gov"
_RESULT_LIMIT = 10
_MAX_RESPONSE_BYTES = 1_000_000
_USER_AGENT = "Oriva/1.0 (https://github.com/MarioSobrado19/Amazon-AI)"
_OBSERVATION_NAMESPACE = UUID("05e4410d-e00d-4819-b542-ff833b20d9d7")


class DocumentaryPresenceStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    NO_DATA = "no_data"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class DocumentaryPresenceFailure:
    code: str
    message: str
    retryable: bool

    def to_dict(self):
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


@dataclass(frozen=True, slots=True)
class DocumentaryPresenceResult:
    """Resultado neutral; deliberadamente no es evidencia del dominio."""

    status: DocumentaryPresenceStatus
    probe_id: str
    completed_at: datetime
    observation: FrozenMapping | None = None
    missing_information: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    failure: DocumentaryPresenceFailure | None = None
    probe_version: str = PROBE_VERSION

    def __post_init__(self):
        if not isinstance(self.status, DocumentaryPresenceStatus):
            raise TypeError("status debe ser DocumentaryPresenceStatus")
        if self.completed_at.tzinfo is None or self.completed_at.utcoffset() is None:
            raise ValueError("completed_at requiere zona horaria")
        if self.observation is not None and not isinstance(self.observation, FrozenMapping):
            object.__setattr__(self, "observation", FrozenMapping.from_mapping(self.observation))
        object.__setattr__(self, "missing_information", tuple(self.missing_information))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        if self.status is DocumentaryPresenceStatus.FAILURE and self.failure is None:
            raise ValueError("failure requiere detalle")
        if self.status is not DocumentaryPresenceStatus.FAILURE and self.failure is not None:
            raise ValueError("solo failure puede contener detalle")

    def to_dict(self):
        return {
            "status": self.status.value,
            "probe_id": self.probe_id,
            "completed_at": self.completed_at.isoformat(),
            "observation": self.observation.to_dict() if self.observation else None,
            "missing_information": list(self.missing_information),
            "warnings": list(self.warnings),
            "failure": self.failure.to_dict() if self.failure else None,
            "probe_version": self.probe_version,
        }


class SourceAcquisitionError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class SourceNoData(Exception):
    """La fuente respondió correctamente pero sin registros observables."""


@dataclass(frozen=True, slots=True)
class SourceDocument:
    body: str
    final_url: str
    retrieved_at: datetime
    content_type: str = "application/json"


def normalize_query(value: str) -> str:
    if not isinstance(value, str):
        raise SourceAcquisitionError("invalid_query", "La consulta debe ser texto.", retryable=False)
    normalized = " ".join(value.split())
    if not normalized or len(normalized) > 200:
        raise SourceAcquisitionError(
            "invalid_query", "La consulta debe contener entre 1 y 200 caracteres.", retryable=False,
        )
    return normalized


def build_source_url(query: str) -> str:
    normalized = normalize_query(query)
    return (
        f"{_SOURCE_ROOT}?q={quote_plus(normalized)}&fo=json&c={_RESULT_LIMIT}"
        "&at=results%2Cpagination"
    )


def _official_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == _ALLOWED_HOST
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
        and parsed.path == "/books/"
    )


def _source_url_matches(url: str, query: str) -> bool:
    if not _official_https_url(url):
        return False
    params = parse_qs(urlparse(url).query, keep_blank_values=True)
    return params == {
        "q": [normalize_query(query)],
        "fo": ["json"],
        "c": [str(_RESULT_LIMIT)],
        "at": ["results,pagination"],
    }


class _OfficialRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _official_https_url(newurl):
            raise SourceAcquisitionError(
                "unexpected_redirect",
                "La fuente intentó redirigir fuera del endpoint oficial permitido.",
                retryable=False,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_official_collections(query: str, *, timeout_seconds: float = 10.0) -> SourceDocument:
    source_url = build_source_url(query)
    request = Request(source_url, headers={"Accept": "application/json", "User-Agent": _USER_AGENT})
    try:
        with build_opener(_OfficialRedirectHandler()).open(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            if not _source_url_matches(final_url, query):
                raise SourceAcquisitionError(
                    "unexpected_redirect",
                    "La fuente cambió el alcance semántico de la consulta.",
                    retryable=False,
                )
            content_type = response.headers.get_content_type()
            if content_type != "application/json":
                raise SourceAcquisitionError(
                    "unexpected_content_type", "La fuente oficial no devolvió JSON.", retryable=True,
                )
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise SourceAcquisitionError(
                    "response_too_large", "La respuesta excede el límite permitido.", retryable=False,
                )
            charset = response.headers.get_content_charset() or "utf-8"
            return SourceDocument(raw.decode(charset), final_url, datetime.now(timezone.utc), content_type)
    except SourceAcquisitionError:
        raise
    except HTTPError as error:
        retryable = error.code == 429 or error.code >= 500
        raise SourceAcquisitionError(
            "rate_limited" if error.code == 429 else "http_error",
            f"La fuente oficial respondió con HTTP {error.code}.",
            retryable=retryable,
        ) from error
    except (TimeoutError, socket.timeout) as error:
        raise SourceAcquisitionError("timeout", "La fuente oficial no respondió a tiempo.", retryable=True) from error
    except (URLError, UnicodeError) as error:
        raise SourceAcquisitionError(
            "source_unavailable", "No se pudo leer la fuente oficial.", retryable=True,
        ) from error


def _string_list(value, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} inválido")
    return sorted(set(" ".join(item.split()) for item in value))


def parse_collections_response(body: str, query: str) -> tuple[dict, tuple[str, ...]]:
    """Extrae solo observaciones mínimas; tolera registros aislados incompletos."""
    normalized_query = normalize_query(query)
    try:
        payload = json.loads(body)
    except (TypeError, json.JSONDecodeError) as error:
        raise SourceAcquisitionError(
            "source_format_changed", "La respuesta oficial no contiene JSON válido.", retryable=False,
        ) from error
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise SourceAcquisitionError(
            "source_format_changed", "La respuesta no contiene results válidos.", retryable=False,
        )
    pagination = payload.get("pagination")
    if not isinstance(pagination, dict):
        raise SourceAcquisitionError(
            "source_format_changed", "La respuesta no contiene pagination válida.", retryable=False,
        )
    total = pagination.get("total")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        raise SourceAcquisitionError(
            "source_format_changed", "pagination.total es inválido.", retryable=False,
        )
    if not payload["results"]:
        if total == 0:
            raise SourceNoData("La fuente respondió sin registros observables para la consulta.")
        raise SourceAcquisitionError(
            "incomplete_source_data", "La fuente declaró coincidencias pero no devolvió registros.", retryable=True,
        )

    observations = []
    seen = set()
    invalid_count = 0
    for item in payload["results"]:
        try:
            if not isinstance(item, dict):
                raise ValueError("registro inválido")
            identifier = item.get("id")
            title = item.get("title")
            if not isinstance(identifier, str) or not isinstance(title, str) or not title.strip():
                raise ValueError("identidad incompleta")
            parsed_id = urlparse(identifier)
            if (
                parsed_id.scheme not in ("http", "https")
                or parsed_id.hostname != _ALLOWED_HOST
                or not parsed_id.path.startswith("/item/")
                or parsed_id.username is not None
                or parsed_id.password is not None
                or parsed_id.port not in (None, 443)
            ):
                raise ValueError("identificador ajeno a Library of Congress")
            identifier = parsed_id._replace(scheme="https").geturl()
            if identifier in seen:
                raise SourceAcquisitionError(
                    "ambiguous_source_data", "La fuente devolvió identificadores duplicados.", retryable=False,
                )
            seen.add(identifier)
            date_value = item.get("date")
            if date_value is not None and (not isinstance(date_value, str) or not date_value.strip()):
                raise ValueError("date inválida")
            observations.append({
                "record_id": identifier,
                "title": " ".join(title.split()),
                "date": " ".join(date_value.split()) if date_value else None,
                "formats": _string_list(item.get("original_format"), "original_format"),
                "subjects": _string_list(item.get("subject"), "subject")[:20],
            })
        except SourceAcquisitionError:
            raise
        except ValueError:
            invalid_count += 1

    if not observations:
        raise SourceAcquisitionError(
            "ambiguous_source_data", "Ningún registro pudo verificarse de forma segura.", retryable=False,
        )
    observations.sort(key=lambda item: (item["record_id"], item["title"]))
    warnings = ()
    if invalid_count:
        warnings = (f"Se omitieron {invalid_count} registros incompletos o inválidos.",)
    return ({
        "signal_type": "loc_collections_query_matches",
        "metric": "observable_collection_records",
        "query": normalized_query,
        "query_identity": "user_supplied_exact_text",
        "collection": "books",
        "source_reported_total": total,
        "returned_valid_records": len(observations),
        "observations": observations,
        "marketplace_scope": "none",
        "geographic_scope": "not_commercially_geolocated",
        "currency": None,
    }, warnings)


class LibraryOfCongressDocumentaryPresenceProbe:
    """Probe experimental no registrable como ResearchCapability."""

    probe_id = PROBE_ID

    def __init__(self, fetcher: Callable[[str], SourceDocument] = fetch_official_collections):
        self._fetcher = fetcher

    def observe(self, query: str) -> DocumentaryPresenceResult:
        try:
            query = normalize_query(query)
            document = self._fetcher(query)
            if not _source_url_matches(document.final_url, query):
                raise SourceAcquisitionError(
                    "untrusted_source", "El documento no coincide con la consulta oficial permitida.", retryable=False,
                )
            values, parse_warnings = parse_collections_response(document.body, query)
            canonical = json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            digest = sha256(canonical.encode("utf-8")).hexdigest()
            identity = "|".join((document.final_url, document.retrieved_at.isoformat(), digest))
            observation = {
                **values,
                "observation_id": str(uuid5(_OBSERVATION_NAMESPACE, identity)),
                "subject_type": "documentary_presence_query",
                "semantic_sha256": digest,
                "source": SOURCE_NAME,
                "source_reference": document.final_url,
                "observed_at": document.retrieved_at.isoformat(),
                "retrieved_at": document.retrieved_at.isoformat(),
                "freshness": "captured_current",
                "verification": "source_response_verified",
                "confidence": "medium",
                "version": PARSER_VERSION,
                "region": None,
                "marketplace_id": None,
                "limitations": (
                    "Es una fotografía de registros bibliográficos coincidentes en una colección pública, no un censo de productos o vendedores.",
                    "No mide competencia comercial, saturación, ventas, intención de compra, cuota de mercado, precios ni disponibilidad.",
                    "La consulta fue suministrada como texto exacto; V1 no resuelve identidad de producto, categoría, marca, listing ni marketplace.",
                    "Los resultados pueden incluir coincidencias textuales no equivalentes al producto o categoría que el usuario investiga.",
                    "La colección no representa un marketplace y no tiene alcance regional comercial.",
                    "source_reported_total describe coincidencias declaradas por la fuente y no número de competidores.",
                    "La vigencia decisional disminuye con el tiempo, pero la observación histórica permanece válida como fotografía de la consulta.",
                ),
            }
            status = DocumentaryPresenceStatus.PARTIAL if parse_warnings else DocumentaryPresenceStatus.SUCCESS
            warnings = tuple(parse_warnings) + (
                "Presencia documental observable; no es evidencia de competencia comercial.",
            )
            missing = (
                "Faltan datos verificables de listings, vendedores, precios, disponibilidad y marketplace.",
            ) if status is DocumentaryPresenceStatus.PARTIAL else ()
            return DocumentaryPresenceResult(
                status, self.probe_id, document.retrieved_at,
                FrozenMapping.from_mapping(observation), missing, warnings,
            )
        except SourceNoData:
            completed_at = datetime.now(timezone.utc)
            return DocumentaryPresenceResult(
                DocumentaryPresenceStatus.NO_DATA, self.probe_id, completed_at,
                missing_information=("La fuente no devolvió registros bibliográficos verificables para la consulta.",),
                warnings=("NO_DATA solo describe la consulta documental; no informa sobre competencia.",),
            )
        except SourceAcquisitionError as error:
            failed_at = datetime.now(timezone.utc)
            failure = DocumentaryPresenceFailure(error.code, str(error), error.retryable)
            return DocumentaryPresenceResult(
                DocumentaryPresenceStatus.FAILURE, self.probe_id, failed_at, failure=failure,
            )
