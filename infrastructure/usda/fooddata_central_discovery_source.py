"""DiscoverySource para productos de marca de USDA FoodData Central.

INTERNAL / CONFIDENTIAL — ORIVA. La presencia en FoodData Central confirma
únicamente una identidad de catálogo alimentario. No demuestra disponibilidad,
demanda, ventas, competencia, precio, margen, elegibilidad ni rentabilidad.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import socket
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from application.discovery_models import (
    DiscoveryRequest,
    DiscoverySignal,
    DiscoverySignalType,
    DiscoverySourceKind,
    DiscoverySourceResult,
    DiscoverySourceStatus,
    HypothesisIdentityKind,
)
from domain.enums import FreshnessStatus, VerificationStatus
from domain.value_objects import Region


SOURCE_ID = "usda-fooddata-central-branded-discovery-v1"
SOURCE_NAME = "USDA FoodData Central — Global Branded Foods Database"
SOURCE_VERSION = "usda-fdc-branded-search/1.0"
API_ROOT = "https://api.nal.usda.gov/fdc/v1/foods/search"
DOCUMENTATION_URL = "https://fdc.nal.usda.gov/api-guide/"
DEMO_KEY = "DEMO_KEY"
_ALLOWED_HOST = "api.nal.usda.gov"
_MAX_RESPONSE_BYTES = 2_000_000
_MAX_RESULTS = 10
_USER_AGENT = "Oriva/1.0 (https://github.com/MarioSobrado19/Amazon-AI)"


class SourceAcquisitionError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class SourceNoData(Exception):
    """La fuente respondió correctamente pero sin productos utilizables."""


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
    if not normalized or len(normalized) > 120:
        raise SourceAcquisitionError(
            "invalid_query", "La consulta debe contener entre 1 y 120 caracteres.", retryable=False,
        )
    return normalized


def _official_api_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == _ALLOWED_HOST
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
        and parsed.path == "/fdc/v1/foods/search"
    )


class _OfficialRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _official_api_url(newurl):
            raise SourceAcquisitionError(
                "unexpected_redirect", "USDA redirigió fuera del endpoint permitido.", retryable=False,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _request_once(query: str, hard_cap: int, timeout_seconds: float) -> SourceDocument:
    payload = json.dumps({
        "query": query,
        "dataType": ["Branded"],
        "pageSize": hard_cap,
        "pageNumber": 1,
        "requireAllWords": True,
    }).encode("utf-8")
    url = f"{API_ROOT}?{urlencode({'api_key': DEMO_KEY})}"
    request = Request(
        url,
        data=payload,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": _USER_AGENT},
    )
    try:
        with build_opener(_OfficialRedirectHandler()).open(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            if not _official_api_url(final_url):
                raise SourceAcquisitionError(
                    "unexpected_redirect", "La respuesta no procede del endpoint oficial de USDA.", retryable=False,
                )
            if response.headers.get_content_type() != "application/json":
                raise SourceAcquisitionError(
                    "unexpected_content_type", "USDA no devolvió JSON.", retryable=True,
                )
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise SourceAcquisitionError(
                    "response_too_large", "La respuesta de USDA excede el límite permitido.", retryable=False,
                )
            charset = response.headers.get_content_charset() or "utf-8"
            return SourceDocument(raw.decode(charset), final_url, datetime.now(timezone.utc))
    except SourceAcquisitionError:
        raise
    except HTTPError as error:
        retryable = error.code == 429 or error.code >= 500
        code = "rate_limited" if error.code == 429 else "http_error"
        raise SourceAcquisitionError(
            code, f"USDA respondió con HTTP {error.code}.", retryable=retryable,
        ) from error
    except (TimeoutError, socket.timeout) as error:
        raise SourceAcquisitionError("timeout", "USDA no respondió a tiempo.", retryable=True) from error
    except (URLError, UnicodeError) as error:
        raise SourceAcquisitionError(
            "source_unavailable", "No se pudo leer USDA FoodData Central.", retryable=True,
        ) from error


def fetch_official_branded_foods(
    query: str,
    hard_cap: int,
    *,
    timeout_seconds: float = 10.0,
    retry_delays: tuple[float, ...] = (0.25,),
    sleeper: Callable[[float], None] = time.sleep,
) -> SourceDocument:
    """Hace como máximo un reintento prudente ante fallos transitorios."""
    normalized = normalize_query(query)
    if not isinstance(hard_cap, int) or isinstance(hard_cap, bool) or not 1 <= hard_cap <= _MAX_RESULTS:
        raise SourceAcquisitionError("invalid_limit", "hard_cap debe estar entre 1 y 10.", retryable=False)
    attempts = len(retry_delays) + 1
    for index in range(attempts):
        try:
            return _request_once(normalized, hard_cap, timeout_seconds)
        except SourceAcquisitionError as error:
            if not error.retryable or index == attempts - 1:
                raise
            sleeper(retry_delays[index])
    raise AssertionError("unreachable")


def _optional_text(item: dict, field: str) -> str | None:
    value = item.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} debe ser texto")
    normalized = " ".join(value.split())
    return normalized or None


def _iso_date(value, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} debe ser fecha ISO")
    return date.fromisoformat(value).isoformat()


def parse_branded_foods(body: str, query: str, hard_cap: int) -> tuple[tuple[dict, ...], tuple[str, ...]]:
    """Extrae campos mínimos; no conserva ingredientes ni nutrición."""
    normalized_query = normalize_query(query)
    try:
        payload = json.loads(body)
    except (TypeError, json.JSONDecodeError) as error:
        raise SourceAcquisitionError(
            "source_format_changed", "USDA no devolvió JSON válido.", retryable=False,
        ) from error
    if not isinstance(payload, dict) or not isinstance(payload.get("foods"), list):
        raise SourceAcquisitionError(
            "source_format_changed", "La respuesta no contiene foods válidos.", retryable=False,
        )
    total_hits = payload.get("totalHits")
    if not isinstance(total_hits, int) or isinstance(total_hits, bool) or total_hits < 0:
        raise SourceAcquisitionError(
            "source_format_changed", "totalHits es inválido.", retryable=False,
        )
    if not payload["foods"]:
        raise SourceNoData("USDA respondió sin productos para la consulta.")

    products = []
    warnings = []
    seen = set()
    for raw in payload["foods"][:hard_cap]:
        try:
            if not isinstance(raw, dict):
                raise ValueError("registro no es objeto")
            fdc_id = raw.get("fdcId")
            description = _optional_text(raw, "description")
            data_type = _optional_text(raw, "dataType")
            market_country = _optional_text(raw, "marketCountry")
            if not isinstance(fdc_id, int) or isinstance(fdc_id, bool) or fdc_id <= 0:
                raise ValueError("fdcId inválido")
            if not description or data_type != "Branded" or market_country not in ("US", "United States"):
                raise ValueError("identidad Branded US incompleta")
            if fdc_id in seen:
                raise SourceAcquisitionError(
                    "ambiguous_source_data", "USDA devolvió fdcId duplicado.", retryable=False,
                )
            seen.add(fdc_id)
            products.append({
                "fdc_id": fdc_id,
                "identity": f"USDA FDC {fdc_id}: {description}",
                "description": description,
                "gtin_upc": _optional_text(raw, "gtinUpc"),
                "brand_owner": _optional_text(raw, "brandOwner"),
                "brand_name": _optional_text(raw, "brandName"),
                "category": _optional_text(raw, "foodCategory"),
                "market_country": "US",
                "data_source": _optional_text(raw, "dataSource"),
                "published_date": _iso_date(raw.get("publishedDate"), "publishedDate"),
                "modified_date": _iso_date(raw.get("modifiedDate"), "modifiedDate"),
                "query": normalized_query,
            })
        except SourceAcquisitionError:
            raise
        except (TypeError, ValueError) as error:
            warnings.append(f"Se omitió un registro USDA inválido: {error}.")
    if not products:
        if total_hits == 0:
            raise SourceNoData("USDA no declaró coincidencias para la consulta.")
        raise SourceAcquisitionError(
            "incomplete_source_data", "USDA declaró coincidencias pero ninguna identidad Branded US válida.", retryable=False,
        )
    return tuple(products), tuple(warnings)


class UsdaFoodDataCentralDiscoverySource:
    source_id = SOURCE_ID

    def __init__(
        self,
        query: str,
        *,
        hard_cap: int = 5,
        fetcher: Callable[[str, int], SourceDocument] = fetch_official_branded_foods,
    ):
        self._query = normalize_query(query)
        if not isinstance(hard_cap, int) or isinstance(hard_cap, bool) or not 1 <= hard_cap <= _MAX_RESULTS:
            raise SourceAcquisitionError("invalid_limit", "hard_cap debe estar entre 1 y 10.", retryable=False)
        self._hard_cap = hard_cap
        self._fetcher = fetcher

    def collect(self, request: DiscoveryRequest) -> DiscoverySourceResult:
        now = datetime.now(timezone.utc)
        if request.region is not None and request.region.country_code != "US":
            return DiscoverySourceResult(
                self.source_id,
                DiscoverySourceStatus.NO_DATA,
                now,
                missing_information=("USDA Branded Foods V1 solo admite productos declarados para mercado US.",),
            )
        try:
            document = self._fetcher(self._query, self._hard_cap)
            if not _official_api_url(document.final_url):
                raise SourceAcquisitionError(
                    "untrusted_source", "El documento no procede del endpoint oficial de USDA.", retryable=False,
                )
            products, parser_warnings = parse_branded_foods(document.body, self._query, self._hard_cap)
            signals = tuple(
                DiscoverySignal(
                    DiscoverySignalType.CATALOG_PRESENCE,
                    HypothesisIdentityKind.PRODUCT,
                    product["identity"],
                    SOURCE_NAME,
                    DiscoverySourceKind.REAL,
                    document.retrieved_at,
                    document.retrieved_at,
                    FreshnessStatus.CURRENT,
                    VerificationStatus.PARTIAL,
                    SOURCE_VERSION,
                    value={
                        **product,
                        "classification": "REAL CATALOG PRESENCE — NOT DEMAND, SALES OR PROFITABILITY",
                        "license": "CC0 1.0",
                    },
                    source_reference=f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{product['fdc_id']}/nutrients",
                    region=Region("US"),
                    limitations=(
                        "FoodData Central registra productos alimentarios; no es un marketplace ni confirma disponibilidad.",
                        "La presencia de catálogo no demuestra demanda, ventas, competencia, precio, margen ni rentabilidad.",
                        "Los datos Branded proceden principalmente de etiquetas y proveedores; pueden ser incompletos o cambiar.",
                        "La consulta solo cubre alimentos de marca declarados para mercado US.",
                    ),
                )
                for product in products
            )
            status = DiscoverySourceStatus.PARTIAL if parser_warnings else DiscoverySourceStatus.SUCCESS
            return DiscoverySourceResult(
                self.source_id,
                status,
                document.retrieved_at,
                signals,
                missing_information=(
                    "demanda y ventas",
                    "precio y disponibilidad comercial",
                    "competencia",
                    "proveedor, costes y restricciones aplicables",
                ),
                warnings=parser_warnings + (
                    "USDA FoodData Central aporta identidad alimentaria y categoría, no atractivo comercial.",
                ),
            )
        except SourceNoData:
            return DiscoverySourceResult(
                self.source_id,
                DiscoverySourceStatus.NO_DATA,
                now,
                missing_information=("USDA no devolvió identidades Branded US para la consulta.",),
            )
        except SourceAcquisitionError as error:
            return DiscoverySourceResult(
                self.source_id,
                DiscoverySourceStatus.TECHNICAL_FAILURE,
                now,
                missing_information=("La adquisición técnica falló; esto no es evidencia negativa sobre oportunidades.",),
                warnings=(f"Fallo USDA controlado: {error.code}; retryable={str(error.retryable).lower()}.",),
                error_code=error.code,
            )


__all__ = [
    "API_ROOT",
    "DEMO_KEY",
    "DOCUMENTATION_URL",
    "SOURCE_ID",
    "SOURCE_NAME",
    "SOURCE_VERSION",
    "SourceAcquisitionError",
    "SourceDocument",
    "SourceNoData",
    "UsdaFoodDataCentralDiscoverySource",
    "fetch_official_branded_foods",
    "normalize_query",
    "parse_branded_foods",
]
