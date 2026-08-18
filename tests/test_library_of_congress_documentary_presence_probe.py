import json
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from urllib.request import Request

from domain.entities import EvidenceRecord
from infrastructure.library_of_congress import LibraryOfCongressDocumentaryPresenceProbe
from infrastructure.library_of_congress.documentary_presence_probe import (
    DocumentaryPresenceStatus,
    SourceAcquisitionError,
    SourceDocument,
    SourceNoData,
    _OfficialRedirectHandler,
    _USER_AGENT,
    build_source_url,
    normalize_query,
    parse_collections_response,
)
import infrastructure.library_of_congress.documentary_presence_probe as module


NOW = datetime(2026, 8, 18, 4, 0, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures" / "library_of_congress"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def source_document(body=None, url=None, retrieved_at=NOW):
    return SourceDocument(
        body if body is not None else fixture("catalog_matches.json"),
        url or build_source_url("wireless headphones"),
        retrieved_at,
    )


class LibraryOfCongressDocumentaryPresenceProbeTests(unittest.TestCase):
    def probe(self, body=None, url=None, retrieved_at=NOW):
        return LibraryOfCongressDocumentaryPresenceProbe(
            lambda *_: source_document(body, url, retrieved_at),
        )

    def test_es_probe_neutral_y_no_research_capability(self):
        probe = self.probe()
        self.assertFalse(hasattr(probe, "capability_id"))
        self.assertFalse(hasattr(probe, "supported_categories"))
        self.assertFalse(hasattr(probe, "can_handle"))
        self.assertFalse(hasattr(probe, "execute"))
        self.assertTrue(hasattr(probe, "observe"))

    def test_modulo_no_produce_evidence_record_ni_competition_category(self):
        self.assertNotIn("EvidenceRecord", module.__dict__)
        self.assertNotIn("ResearchCategory", module.__dict__)
        result = self.probe().observe("wireless headphones")
        self.assertNotIsInstance(result.observation, EvidenceRecord)

    def test_user_agent_es_identificable(self):
        self.assertIn("Oriva/1.0", _USER_AGENT)
        self.assertIn("https://", _USER_AGENT)

    def test_normaliza_consulta_solo_cosmeticamente(self):
        self.assertEqual(normalize_query("  wireless   headphones  "), "wireless headphones")
        for invalid in (None, "", "   ", "x" * 201):
            with self.subTest(invalid=invalid):
                with self.assertRaises(SourceAcquisitionError):
                    normalize_query(invalid)

    def test_url_limita_host_path_y_parametros(self):
        self.assertEqual(
            build_source_url("wireless headphones"),
            "https://www.loc.gov/books/?q=wireless+headphones&fo=json&c=10&at=results%2Cpagination",
        )

    def test_redirect_externo_credenciales_puerto_y_ruta_se_rechazan(self):
        original = build_source_url("wireless headphones")
        invalid = (
            "https://example.com/books/?q=x",
            "https://user:secret@www.loc.gov/books/?q=x",
            "https://www.loc.gov:8443/books/?q=x",
            "https://www.loc.gov/search/?q=x",
        )
        for url in invalid:
            with self.subTest(url=url):
                with self.assertRaises(SourceAcquisitionError):
                    _OfficialRedirectHandler().redirect_request(Request(original), None, 302, "Found", {}, url)

    def test_parser_conserva_registros_sin_clasificar_competencia(self):
        values, warnings = parse_collections_response(fixture("catalog_matches.json"), "wireless headphones")
        self.assertEqual(values["signal_type"], "loc_collections_query_matches")
        self.assertEqual(values["source_reported_total"], 3)
        self.assertEqual(values["returned_valid_records"], 3)
        self.assertEqual(warnings, ())
        for forbidden in ("score", "ranking", "recommendation", "competition_level"):
            self.assertNotIn(forbidden, values)

    def test_parser_json_invalido_y_estructura_incorrecta_fallan(self):
        for body in ("not json", '{"items": []}', '{"results": [], "pagination": []}'):
            with self.subTest(body=body):
                with self.assertRaises(SourceAcquisitionError) as caught:
                    parse_collections_response(body, "wireless headphones")
                self.assertEqual(caught.exception.code, "source_format_changed")

    def test_cero_registros_es_no_data_documental(self):
        with self.assertRaises(SourceNoData):
            parse_collections_response(fixture("empty.json"), "wireless headphones")

    def test_total_positivo_sin_resultados_es_fallo_incompleto(self):
        with self.assertRaises(SourceAcquisitionError) as caught:
            parse_collections_response('{"pagination":{"total":2},"results":[]}', "wireless headphones")
        self.assertEqual(caught.exception.code, "incomplete_source_data")

    def test_duplicados_se_rechazan(self):
        payload = json.loads(fixture("catalog_matches.json"))
        payload["results"].append(payload["results"][0])
        with self.assertRaises(SourceAcquisitionError) as caught:
            parse_collections_response(json.dumps(payload), "wireless headphones")
        self.assertEqual(caught.exception.code, "ambiguous_source_data")

    def test_un_registro_invalido_produce_partial_con_validos(self):
        result = self.probe(body=fixture("partial.json")).observe("wireless headphones")
        self.assertIs(result.status, DocumentaryPresenceStatus.PARTIAL)
        self.assertEqual(result.observation.to_dict()["returned_valid_records"], 1)
        self.assertTrue(result.missing_information)

    def test_todos_los_registros_invalidos_producen_failure(self):
        body = '{"pagination":{"total":1},"results":[{"id":"bad","title":"x"}]}'
        result = self.probe(body=body).observe("wireless headphones")
        self.assertIs(result.status, DocumentaryPresenceStatus.FAILURE)
        self.assertEqual(result.failure.code, "ambiguous_source_data")

    def test_identificador_http_oficial_se_canonicaliza_a_https(self):
        payload = json.loads(fixture("catalog_matches.json"))
        payload["results"] = [payload["results"][0]]
        payload["pagination"]["total"] = 1
        payload["results"][0]["id"] = "http://www.loc.gov/item/example-003/"
        values, _ = parse_collections_response(json.dumps(payload), "wireless headphones")
        self.assertEqual(values["observations"][0]["record_id"], "https://www.loc.gov/item/example-003/")

    def test_observacion_declara_que_no_es_competencia(self):
        result = self.probe().observe("wireless headphones")
        self.assertIs(result.status, DocumentaryPresenceStatus.SUCCESS)
        observation = result.observation.to_dict()
        self.assertEqual(observation["subject_type"], "documentary_presence_query")
        self.assertIsNone(observation["region"])
        self.assertIsNone(observation["marketplace_id"])
        self.assertTrue(any("No mide competencia comercial" in item for item in observation["limitations"]))
        self.assertTrue(any("no es evidencia de competencia comercial" in item for item in result.warnings))

    def test_no_data_no_informa_sobre_competencia(self):
        result = self.probe(body=fixture("empty.json")).observe("wireless headphones")
        self.assertIs(result.status, DocumentaryPresenceStatus.NO_DATA)
        self.assertIsNone(result.observation)
        self.assertTrue(any("no informa sobre competencia" in item for item in result.warnings))

    def test_timeout_http_y_parser_son_failure_no_observacion_negativa(self):
        for code, retryable in (("timeout", True), ("http_error", True), ("source_format_changed", False)):
            def fail(*_, code=code, retryable=retryable):
                raise SourceAcquisitionError(code, "Fallo técnico controlado.", retryable=retryable)
            with self.subTest(code=code):
                result = LibraryOfCongressDocumentaryPresenceProbe(fail).observe("wireless headphones")
                self.assertIs(result.status, DocumentaryPresenceStatus.FAILURE)
                self.assertEqual(result.failure.code, code)
                self.assertIsNone(result.observation)

    def test_url_final_con_query_cambiada_falla(self):
        result = self.probe(url=build_source_url("different query")).observe("wireless headphones")
        self.assertIs(result.status, DocumentaryPresenceStatus.FAILURE)
        self.assertEqual(result.failure.code, "untrusted_source")

    def test_hash_determinista_ignora_orden_cosmetico(self):
        payload = json.loads(fixture("catalog_matches.json"))
        reordered = json.dumps({
            "results": list(reversed([dict(reversed(list(item.items()))) for item in payload["results"]])),
            "pagination": payload["pagination"],
        })
        first = self.probe().observe("wireless headphones").observation.to_dict()
        second = self.probe(body=reordered).observe("wireless headphones").observation.to_dict()
        self.assertEqual(first["semantic_sha256"], second["semantic_sha256"])

    def test_cambio_material_cambia_hash(self):
        payload = json.loads(fixture("catalog_matches.json"))
        payload["results"][0]["title"] = "Materially changed title"
        first = self.probe().observe("wireless headphones").observation.to_dict()
        second = self.probe(body=json.dumps(payload)).observe("wireless headphones").observation.to_dict()
        self.assertNotEqual(first["semantic_sha256"], second["semantic_sha256"])

    def test_observaciones_historicas_no_se_sobrescriben(self):
        first = self.probe().observe("wireless headphones").observation.to_dict()
        later = self.probe(retrieved_at=NOW + timedelta(days=1)).observe("wireless headphones").observation.to_dict()
        self.assertNotEqual(first["observation_id"], later["observation_id"])
        self.assertEqual(first["semantic_sha256"], later["semantic_sha256"])

    def test_resultado_es_inmutable_y_serializacion_no_expone_estado(self):
        result = self.probe().observe("wireless headphones")
        with self.assertRaises(FrozenInstanceError):
            result.status = DocumentaryPresenceStatus.FAILURE
        serialized = result.to_dict()
        serialized["observation"]["observations"][0]["title"] = "mutated"
        self.assertNotEqual(result.observation.to_dict()["observations"][0]["title"], "mutated")

    def test_no_filtra_secretos(self):
        serialized = json.dumps(self.probe().observe("wireless headphones").to_dict()).casefold()
        for forbidden in ("access_token", "refresh_token", "client_secret", "password", "cookie"):
            self.assertNotIn(forbidden, serialized)

    def test_no_hay_lenguaje_de_conclusion_comercial_en_datos(self):
        observation = self.probe().observe("wireless headphones").observation.to_dict()
        payload = json.dumps({
            key: value for key, value in observation.items() if key != "limitations"
        }, ensure_ascii=False).casefold()
        for phrase in ("competencia alta", "competencia baja", "mercado saturado", "producto ganador"):
            self.assertNotIn(phrase, payload)


if __name__ == "__main__":
    unittest.main()
