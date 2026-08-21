import json
from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.request import Request

from application.discovery_models import (
    DiscoveryRequest,
    DiscoveryRunStatus,
    DiscoverySignalType,
    DiscoverySourceKind,
    DiscoverySourceStatus,
    OpportunityHypothesisState,
)
from application.opportunity_discovery_service import discover_opportunity_hypotheses
from domain.enums import FreshnessStatus, VerificationStatus
from domain.value_objects import Region
from infrastructure.usda.fooddata_central_discovery_source import (
    API_ROOT,
    DEMO_KEY,
    SOURCE_NAME,
    SOURCE_VERSION,
    SourceAcquisitionError,
    SourceDocument,
    SourceNoData,
    UsdaFoodDataCentralDiscoverySource,
    _OfficialRedirectHandler,
    fetch_official_branded_foods,
    normalize_query,
    parse_branded_foods,
)


NOW = datetime(2026, 8, 20, 16, tzinfo=timezone.utc)
FIXTURE = Path(__file__).parent / "fixtures" / "usda_fooddata" / "branded_search_synthetic.json"
CASE_STATUS = Path(__file__).parents[1] / "docs" / "case-studies" / "oriva-0001" / "case_status_v3.json"


def fixture(name="branded_search_synthetic.json"):
    return (FIXTURE.parent / name).read_text(encoding="utf-8")


def source_document(body=None, url=None, retrieved_at=NOW):
    return SourceDocument(
        body if body is not None else fixture(),
        url or f"{API_ROOT}?api_key={DEMO_KEY}",
        retrieved_at,
    )


def request(region="US"):
    return DiscoveryRequest(
        "oriva-case-0001-discovery-v1",
        "oriva-case-0001-objective",
        NOW,
        Region(region),
        750,
        0,
        90,
        10,
    )


class UsdaFoodDataParserTests(unittest.TestCase):
    def test_fixture_sintetico_esta_etiquetado(self):
        self.assertEqual(json.loads(fixture())["classification"], "SYNTHETIC / NOT REAL EVIDENCE")

    def test_query_se_normaliza_y_valida(self):
        self.assertEqual(normalize_query("  protein   bar "), "protein bar")
        for invalid in (None, "", " " * 5, "x" * 121):
            with self.subTest(invalid=invalid):
                with self.assertRaises(SourceAcquisitionError):
                    normalize_query(invalid)

    def test_parser_extrae_solo_identidad_comercial_minima(self):
        products, warnings = parse_branded_foods(fixture(), "protein bar", 5)
        self.assertEqual(len(products), 2)
        self.assertFalse(warnings)
        self.assertEqual(products[0]["fdc_id"], 9000001)
        self.assertEqual(products[0]["gtin_upc"], "00000000000001")
        self.assertEqual(products[0]["category"], "Nutrition Bars")
        self.assertNotIn("ingredients", products[0])
        self.assertNotIn("foodNutrients", products[0])

    def test_parser_normaliza_nombre_oficial_de_mercado_us(self):
        payload = json.loads(fixture())
        payload["foods"][0]["marketCountry"] = "United States"
        products, _ = parse_branded_foods(json.dumps(payload), "protein bar", 5)
        self.assertEqual(products[0]["market_country"], "US")

    def test_parser_rechaza_json_y_schema_invalidos(self):
        for body in ("not-json", "{}", '{"foods": [], "totalHits": "2"}'):
            with self.subTest(body=body):
                with self.assertRaises(SourceAcquisitionError):
                    parse_branded_foods(body, "protein bar", 5)

    def test_respuesta_vacia_es_no_data(self):
        with self.assertRaises(SourceNoData):
            parse_branded_foods('{"totalHits": 0, "foods": []}', "protein bar", 5)

    def test_registro_no_us_se_omite_sin_inventar_region(self):
        payload = json.loads(fixture())
        payload["foods"][0]["marketCountry"] = "CA"
        products, warnings = parse_branded_foods(json.dumps(payload), "protein bar", 5)
        self.assertEqual(len(products), 1)
        self.assertTrue(warnings)

    def test_ids_duplicados_se_rechazan(self):
        payload = json.loads(fixture())
        payload["foods"][1]["fdcId"] = payload["foods"][0]["fdcId"]
        with self.assertRaises(SourceAcquisitionError) as caught:
            parse_branded_foods(json.dumps(payload), "protein bar", 5)
        self.assertEqual(caught.exception.code, "ambiguous_source_data")

    def test_redirect_externo_credenciales_puerto_y_ruta_se_rechazan(self):
        original = f"{API_ROOT}?api_key={DEMO_KEY}"
        invalid = (
            "https://example.com/fdc/v1/foods/search",
            "https://user:secret@api.nal.usda.gov/fdc/v1/foods/search",
            "https://api.nal.usda.gov:8443/fdc/v1/foods/search",
            "https://api.nal.usda.gov/fdc/v1/food/1",
        )
        for url in invalid:
            with self.subTest(url=url):
                with self.assertRaises(SourceAcquisitionError):
                    _OfficialRedirectHandler().redirect_request(Request(original), None, 302, "Found", {}, url)

    def test_reintento_solo_ante_fallo_retryable(self):
        calls = []
        delays = []

        def requester(*_):
            calls.append(1)
            if len(calls) == 1:
                raise SourceAcquisitionError("timeout", "timeout", retryable=True)
            return source_document()

        with patch(
            "infrastructure.usda.fooddata_central_discovery_source._request_once",
            side_effect=requester,
        ):
            result = fetch_official_branded_foods(
                "protein bar", 2, retry_delays=(0.01,), sleeper=delays.append,
            )
        self.assertEqual(result.retrieved_at, NOW)
        self.assertEqual(len(calls), 2)
        self.assertEqual(delays, [0.01])

    def test_no_reintenta_error_no_retryable(self):
        with patch(
            "infrastructure.usda.fooddata_central_discovery_source._request_once",
            side_effect=SourceAcquisitionError("schema", "schema", retryable=False),
        ) as requester:
            with self.assertRaises(SourceAcquisitionError):
                fetch_official_branded_foods("protein bar", 2, retry_delays=(0.01,), sleeper=lambda _: None)
        self.assertEqual(requester.call_count, 1)


class UsdaFoodDataDiscoverySourceTests(unittest.TestCase):
    def source(self, body=None):
        return UsdaFoodDataCentralDiscoverySource(
            "protein bar", hard_cap=5, fetcher=lambda *_: source_document(body=body),
        )

    def test_produce_catalog_presence_real_no_demanda(self):
        result = self.source().collect(request())
        self.assertIs(result.status, DiscoverySourceStatus.SUCCESS)
        self.assertEqual(len(result.signals), 2)
        for signal in result.signals:
            self.assertIs(signal.signal_type, DiscoverySignalType.CATALOG_PRESENCE)
            self.assertIs(signal.source_kind, DiscoverySourceKind.REAL)
            self.assertEqual(signal.source, SOURCE_NAME)
            self.assertEqual(signal.method_version, SOURCE_VERSION)
            self.assertEqual(signal.region, Region("US"))
            self.assertIsNone(signal.marketplace_id)
            self.assertIs(signal.freshness, FreshnessStatus.CURRENT)
            self.assertIs(signal.verification_status, VerificationStatus.PARTIAL)
            serialized = json.dumps(signal.to_dict()).casefold()
            self.assertNotIn("demand_score", serialized)
            self.assertNotIn("sales", signal.value.to_dict())
            self.assertNotIn("profit", signal.value.to_dict())
            self.assertNotIn("api_key", signal.source_reference)

    def test_pipeline_crea_hipotesis_surfaced_no_research_ready(self):
        result = discover_opportunity_hypotheses(request(), (self.source(),), generated_at=NOW)
        self.assertIs(result.status, DiscoveryRunStatus.HOLD_EVIDENCE_ACQUISITION)
        self.assertEqual(len(result.real_hypotheses), 2)
        self.assertTrue(all(item.state is OpportunityHypothesisState.SURFACED for item in result.hypotheses))
        self.assertTrue(all(len(item.research_needs) == 7 for item in result.hypotheses))

    def test_no_data_no_es_fallo_tecnico(self):
        result = self.source('{"totalHits": 0, "foods": []}').collect(request())
        self.assertIs(result.status, DiscoverySourceStatus.NO_DATA)
        self.assertFalse(result.signals)

    def test_schema_roto_es_fallo_tecnico_no_evidencia_negativa(self):
        result = self.source("{}").collect(request())
        self.assertIs(result.status, DiscoverySourceStatus.TECHNICAL_FAILURE)
        self.assertEqual(result.error_code, "source_format_changed")
        self.assertFalse(result.signals)
        self.assertTrue(any("no es evidencia negativa" in item for item in result.missing_information))

    def test_region_fuera_de_us_es_no_data_explicito(self):
        result = self.source().collect(request("CA"))
        self.assertIs(result.status, DiscoverySourceStatus.NO_DATA)
        self.assertFalse(result.signals)

    def test_hard_cap_invalido_se_rechaza(self):
        for invalid in (0, 11, True):
            with self.subTest(invalid=invalid):
                with self.assertRaises(SourceAcquisitionError):
                    UsdaFoodDataCentralDiscoverySource("protein bar", hard_cap=invalid)

    def test_serializacion_no_expone_demo_key_como_credencial(self):
        result = self.source().collect(request())
        payload = json.dumps({"signals": [item.to_dict() for item in result.signals]})
        self.assertNotIn("api_key", payload)
        self.assertNotIn(DEMO_KEY, payload)

    def test_caso_0001_conserva_hold_candidatos_vacios_y_capital_cero(self):
        status = json.loads(CASE_STATUS.read_text(encoding="utf-8"))
        self.assertEqual(status["status"], "hold_evidence_acquisition")
        self.assertEqual(status["current_candidates"], [])
        self.assertEqual(status["discovery"]["research_ready_hypotheses"], 0)
        self.assertEqual(status["capital"]["currently_authorized"]["amount"], "0.00")
        self.assertEqual(status["capital"]["spent"]["amount"], "0.00")
        self.assertEqual(status["capital"]["at_risk"]["amount"], "0.00")


if __name__ == "__main__":
    unittest.main()
