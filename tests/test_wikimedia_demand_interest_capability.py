import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import unittest
from urllib.request import Request

from application.research_models import (
    EvidenceAccess,
    EvidenceVisibility,
    ResearchCapabilityRequest,
    ResearchCapabilityResultStatus,
    ResearchExecutionContext,
)
from application.research_orchestration_service import create_research_plan, execute_research_plan
from domain.enums import (
    EvidenceType,
    FreshnessStatus,
    ResearchCategory,
    ResearchQuestionStatus,
    VerificationStatus,
)
from domain.value_objects import Region, ResearchNeed, ResearchQuestion
from infrastructure.wikimedia.demand_interest_capability import (
    PARSER_VERSION,
    SourceAcquisitionError,
    SourceDocument,
    SourceNoData,
    WikimediaPageviewsDemandCapability,
    _USER_AGENT,
    _OfficialRedirectHandler,
    build_source_url,
    parse_pageviews,
    parse_time_scope,
)
from tests.test_research_foundation import assess


NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
START = date(2026, 8, 1)
END = date(2026, 8, 3)
FIXTURES = Path(__file__).parent / "fixtures" / "wikimedia_pageviews"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def request(**changes):
    values = {
        "task_id": "task-demand-1",
        "category": ResearchCategory.DEMAND,
        "question": "¿Cuántas vistas recibió este artículo de Wikipedia?",
        "subject_type": "wikipedia_article",
        "subject_id": "Headphones",
        "execution_context": ResearchExecutionContext("project-a", "request-1", NOW),
        "time_scope": "2026-08-01/2026-08-03",
    }
    values.update(changes)
    return ResearchCapabilityRequest(**values)


def source_document(body=None, url=None, retrieved_at=NOW):
    return SourceDocument(
        body if body is not None else fixture("wireless_headphones_20260801_20260803.json"),
        url or build_source_url("Headphones", START, END),
        retrieved_at,
    )


class WikimediaPageviewsDemandCapabilityTests(unittest.TestCase):
    def test_user_agent_es_identificable_y_tiene_contacto(self):
        self.assertIn("Oriva/1.0", _USER_AGENT)
        self.assertIn("https://", _USER_AGENT)

    def test_parser_conserva_serie_diaria_y_total_exacto(self):
        values = parse_pageviews(
            fixture("wireless_headphones_20260801_20260803.json"), "Headphones", START, END,
        )
        self.assertEqual(values["signal_type"], "wikipedia_article_pageviews")
        self.assertEqual(values["metric"], "page_views")
        self.assertEqual(values["total_views"], 3725)
        self.assertEqual([item["views"] for item in values["observations"]], [1240, 1175, 1310])

    def test_parser_rechaza_json_invalido(self):
        with self.assertRaises(SourceAcquisitionError) as caught:
            parse_pageviews("not json", "Headphones", START, END)
        self.assertEqual(caught.exception.code, "source_format_changed")

    def test_parser_rechaza_estructura_cambiada(self):
        with self.assertRaises(SourceAcquisitionError):
            parse_pageviews('{"results": []}', "Headphones", START, END)

    def test_parser_vacio_es_no_data_y_no_evidencia_negativa(self):
        with self.assertRaises(SourceNoData):
            parse_pageviews(fixture("empty.json"), "Headphones", START, END)

    def test_parser_rechaza_dia_faltante_sin_rellenarlo_con_cero(self):
        with self.assertRaises(SourceAcquisitionError) as caught:
            parse_pageviews(fixture("missing_day.json"), "Headphones", START, END)
        self.assertEqual(caught.exception.code, "incomplete_source_data")

    def test_parser_rechaza_fecha_duplicada(self):
        payload = json.loads(fixture("wireless_headphones_20260801_20260803.json"))
        payload["items"].append(payload["items"][0])
        with self.assertRaises(SourceAcquisitionError) as caught:
            parse_pageviews(json.dumps(payload), "Headphones", START, END)
        self.assertEqual(caught.exception.code, "ambiguous_source_data")

    def test_parser_rechaza_articulo_distinto(self):
        payload = json.loads(fixture("wireless_headphones_20260801_20260803.json"))
        payload["items"][0]["article"] = "Earphone"
        with self.assertRaises(SourceAcquisitionError) as caught:
            parse_pageviews(json.dumps(payload), "Headphones", START, END)
        self.assertEqual(caught.exception.code, "ambiguous_source_data")

    def test_parser_rechaza_agente_que_incluye_spiders(self):
        payload = json.loads(fixture("wireless_headphones_20260801_20260803.json"))
        payload["items"][0]["agent"] = "all-agents"
        with self.assertRaises(SourceAcquisitionError):
            parse_pageviews(json.dumps(payload), "Headphones", START, END)

    def test_parser_rechaza_views_negativas_booleanas_o_texto(self):
        for invalid in (-1, True, "1240"):
            with self.subTest(invalid=invalid):
                payload = json.loads(fixture("wireless_headphones_20260801_20260803.json"))
                payload["items"][0]["views"] = invalid
                with self.assertRaises(SourceAcquisitionError):
                    parse_pageviews(json.dumps(payload), "Headphones", START, END)

    def test_time_scope_es_explicito_ordenado_y_acotado(self):
        self.assertEqual(parse_time_scope("2026-08-01/2026-08-03"), (START, END))
        for invalid in (None, "20260801/20260803", "2026-08-03/2026-08-01", "2024-01-01/2026-01-02"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(SourceAcquisitionError):
                    parse_time_scope(invalid)

    def test_url_codifica_titulo_y_fija_parametros_semanticos(self):
        url = build_source_url("Noise-cancelling headphones", START, END)
        self.assertIn("Noise-cancelling_headphones", url)
        self.assertIn("/en.wikipedia.org/all-access/user/", url)
        self.assertTrue(url.endswith("/daily/20260801/20260803"))

    def test_redirect_interno_al_endpoint_permitido(self):
        url = build_source_url("Headphones", START, END)
        redirected = _OfficialRedirectHandler().redirect_request(
            Request(url), None, 301, "Moved", {}, url,
        )
        self.assertEqual(redirected.full_url, url)

    def test_redirect_externo_credenciales_puerto_y_ruta_se_rechazan(self):
        original = build_source_url("Headphones", START, END)
        invalid_urls = (
            "https://example.com/api/rest_v1/metrics/pageviews/per-article/x",
            "https://user:secret@wikimedia.org/api/rest_v1/metrics/pageviews/per-article/x",
            "https://wikimedia.org:8443/api/rest_v1/metrics/pageviews/per-article/x",
            "https://wikimedia.org/wiki/Headphones",
        )
        for invalid in invalid_urls:
            with self.subTest(invalid=invalid):
                with self.assertRaises(SourceAcquisitionError):
                    _OfficialRedirectHandler().redirect_request(
                        Request(original), None, 302, "Found", {}, invalid,
                    )

    def test_can_handle_solo_demanda_global_sin_marketplace(self):
        capability = WikimediaPageviewsDemandCapability(lambda *_: source_document())
        self.assertTrue(capability.can_handle(request()))
        self.assertFalse(capability.can_handle(request(category=ResearchCategory.COMPETITION)))
        self.assertFalse(capability.can_handle(request(region=Region("US"))))
        self.assertFalse(capability.can_handle(request(marketplace_id="amazon-us")))
        self.assertFalse(capability.can_handle(request(subject_type="product")))

    def test_requiere_titulo_de_articulo_explicito_sin_entity_resolution(self):
        capability = WikimediaPageviewsDemandCapability(lambda *_: source_document())
        self.assertFalse(capability.can_handle(request(subject_type="product_idea")))
        self.assertFalse(capability.can_handle(request(subject_type="product")))
        self.assertTrue(capability.can_handle(request(subject_type="wikipedia_article")))

    def test_rechaza_preguntas_comerciales_fuera_de_alcance(self):
        capability = WikimediaPageviewsDemandCapability(lambda *_: source_document())
        incompatible = (
            "¿Cuántas unidades se venden?",
            "¿Existe demanda suficiente para vender este producto?",
            "¿Cuál es la demanda en Amazon US?",
            "¿Cuál es la conversión de ventas?",
        )
        for question in incompatible:
            with self.subTest(question=question):
                self.assertFalse(capability.can_handle(request(question=question)))

    def test_evidencia_es_trazable_verificada_y_semanticamente_limitada(self):
        result = WikimediaPageviewsDemandCapability(lambda *_: source_document()).execute(request())
        self.assertIs(result.status, ResearchCapabilityResultStatus.SUCCESS)
        self.assertEqual(len(result.evidence), 1)
        evidence = result.evidence[0]
        value = evidence.value.to_dict()
        self.assertIs(evidence.verification_status, VerificationStatus.VERIFIED)
        self.assertIs(evidence.freshness, FreshnessStatus.CURRENT)
        self.assertEqual(evidence.version, PARSER_VERSION)
        self.assertEqual(evidence.source, "Wikimedia Analytics API")
        self.assertEqual(evidence.source_reference, build_source_url("Headphones", START, END))
        self.assertEqual(evidence.retrieved_at, NOW)
        self.assertIsNone(evidence.region)
        self.assertIsNone(evidence.marketplace_id)
        self.assertEqual(value["geographic_scope"], "not_geolocated")
        self.assertEqual(len(value["semantic_sha256"]), 64)
        self.assertTrue(any("No mide búsquedas, ventas" in item for item in evidence.limitations))
        self.assertTrue(any("título del artículo fue suministrado" in item for item in evidence.limitations))
        self.assertTrue(any("no evidencia de ventas" in item for item in result.warnings))

    def test_huella_semantica_no_depende_del_orden_json(self):
        payload = json.loads(fixture("wireless_headphones_20260801_20260803.json"))
        reordered = json.dumps({"items": [dict(reversed(list(item.items()))) for item in payload["items"]]})
        first = WikimediaPageviewsDemandCapability(lambda *_: source_document()).execute(request()).evidence[0]
        second = WikimediaPageviewsDemandCapability(
            lambda *_: source_document(body=reordered)
        ).execute(request()).evidence[0]
        self.assertEqual(first.value.to_dict()["semantic_sha256"], second.value.to_dict()["semantic_sha256"])

    def test_misma_recuperacion_es_idempotente_y_otra_es_historica(self):
        first = WikimediaPageviewsDemandCapability(lambda *_: source_document()).execute(request()).evidence[0]
        same = WikimediaPageviewsDemandCapability(lambda *_: source_document()).execute(request()).evidence[0]
        later = WikimediaPageviewsDemandCapability(
            lambda *_: source_document(retrieved_at=NOW + timedelta(hours=1))
        ).execute(request()).evidence[0]
        self.assertEqual(first.evidence_id, same.evidence_id)
        self.assertNotEqual(first.evidence_id, later.evidence_id)
        self.assertEqual(first.value.to_dict()["semantic_sha256"], later.value.to_dict()["semantic_sha256"])

    def test_documento_fuera_del_endpoint_oficial_falla_sin_evidencia(self):
        result = WikimediaPageviewsDemandCapability(
            lambda *_: source_document(url="https://example.com/pageviews")
        ).execute(request())
        self.assertIs(result.status, ResearchCapabilityResultStatus.FAILED)
        self.assertEqual(result.failure.code, "untrusted_source")
        self.assertFalse(result.evidence)

    def test_timeout_permanece_fallo_tecnico(self):
        def timeout(*_):
            raise SourceAcquisitionError("timeout", "La fuente no respondió.", retryable=True)

        result = WikimediaPageviewsDemandCapability(timeout).execute(request())
        self.assertIs(result.status, ResearchCapabilityResultStatus.FAILED)
        self.assertEqual(result.failure.code, "timeout")
        self.assertTrue(result.failure.retryable)
        self.assertFalse(result.evidence)

    def test_http_error_permanece_fallo_y_no_cero_demanda(self):
        def http_error(*_):
            raise SourceAcquisitionError(
                "http_error", "La fuente oficial respondió con HTTP 503.", retryable=True,
            )

        result = WikimediaPageviewsDemandCapability(http_error).execute(request())
        self.assertIs(result.status, ResearchCapabilityResultStatus.FAILED)
        self.assertEqual(result.failure.code, "http_error")
        self.assertTrue(result.failure.retryable)
        self.assertFalse(result.evidence)

    def test_no_data_no_fabrica_cero_ni_evidencia_negativa(self):
        result = WikimediaPageviewsDemandCapability(
            lambda *_: source_document(body=fixture("empty.json"))
        ).execute(request())
        self.assertIs(result.status, ResearchCapabilityResultStatus.NO_DATA)
        self.assertFalse(result.evidence)
        self.assertIsNone(result.failure)
        self.assertTrue(any("no afirma ausencia" in item for item in result.warnings))

    def test_request_incompatible_falla_explicitamente(self):
        result = WikimediaPageviewsDemandCapability(lambda *_: source_document()).execute(
            request(region=Region("US"))
        )
        self.assertIs(result.status, ResearchCapabilityResultStatus.FAILED)
        self.assertEqual(result.failure.code, "unsupported_request")

    def test_vertical_need_plan_capability_evidence_assessment(self):
        baseline = assess()
        need = ResearchNeed(
            "wikipedia_article", "Headphones", ResearchCategory.DEMAND,
            "Falta una señal indirecta de atención al artículo.", "high", False,
            (EvidenceType.DATA,), missing_information=("page views históricas del artículo",),
        )
        question = ResearchQuestion(
            need.need_id,
            "¿Cuántas vistas recibió este artículo de Wikipedia?",
            "wikipedia_article",
            "Headphones",
            (EvidenceType.DATA,),
            ResearchQuestionStatus.PENDING,
            time_scope="2026-08-01/2026-08-03",
        )
        assessment = replace(
            baseline,
            needs=(need,),
            questions=(question,),
            evidence=(),
            findings=(),
            conflicts=(),
        )
        capability = WikimediaPageviewsDemandCapability(lambda *_: source_document())
        context = request().execution_context
        plan = create_research_plan(
            assessment=assessment,
            capabilities=(capability,),
            execution_context=context,
            created_at=NOW,
        )
        result = execute_research_plan(
            plan=plan,
            assessment=assessment,
            capabilities=(capability,),
            execution_context=context,
            generated_at=NOW,
        )
        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.completed_tasks), 1)
        self.assertEqual(len(result.evidence_obtained), 1)
        self.assertEqual(result.coverage[0].status.value, "covered")
        self.assertEqual(result.evidence_obtained[0].category, ResearchCategory.DEMAND)

    def test_evidencia_global_no_satisface_need_regional(self):
        capability = WikimediaPageviewsDemandCapability(lambda *_: source_document())
        evidence = capability.execute(request()).evidence[0]
        baseline = assess()
        need = ResearchNeed(
            "wikipedia_article", "Headphones", ResearchCategory.DEMAND,
            "Se requiere evidencia comercial regional US.", "high", True,
            (EvidenceType.DATA,), missing_information=("demanda regional US",),
        )
        question = ResearchQuestion(
            need.need_id, "¿Existe demanda comercial en US?", "wikipedia_article",
            "Headphones", (EvidenceType.DATA,), ResearchQuestionStatus.PENDING,
            region=Region("US"), time_scope="2026-08-01/2026-08-03",
        )
        assessment = replace(
            baseline, needs=(need,), questions=(question,), evidence=(evidence,),
            findings=(), conflicts=(),
        )
        access = EvidenceAccess(
            evidence.evidence_id, EvidenceVisibility.PUBLIC_REUSABLE,
            time_scope=question.time_scope,
            applicable_question_ids=(question.question_id,),
        )
        plan = create_research_plan(
            assessment=assessment, capabilities=(capability,),
            execution_context=request().execution_context,
            evidence_access=(access,), created_at=NOW,
        )
        self.assertFalse(any(task.state.value == "skipped_reused" for task in plan.tasks))

    def test_evidencia_global_no_satisface_need_de_marketplace(self):
        capability = WikimediaPageviewsDemandCapability(lambda *_: source_document())
        evidence = capability.execute(request()).evidence[0]
        baseline = assess()
        need = ResearchNeed(
            "wikipedia_article", "Headphones", ResearchCategory.DEMAND,
            "Se requiere evidencia comercial del marketplace.", "high", True,
            (EvidenceType.DATA,), missing_information=("demanda del marketplace",),
        )
        question = ResearchQuestion(
            need.need_id, "¿Cuál es la demanda en Amazon US?", "wikipedia_article",
            "Headphones", (EvidenceType.DATA,), ResearchQuestionStatus.PENDING,
            marketplace_id="amazon-us", time_scope="2026-08-01/2026-08-03",
        )
        assessment = replace(
            baseline, needs=(need,), questions=(question,), evidence=(evidence,),
            findings=(), conflicts=(),
        )
        access = EvidenceAccess(
            evidence.evidence_id, EvidenceVisibility.PUBLIC_REUSABLE,
            time_scope=question.time_scope,
            applicable_question_ids=(question.question_id,),
        )
        plan = create_research_plan(
            assessment=assessment, capabilities=(capability,),
            execution_context=request().execution_context,
            evidence_access=(access,), created_at=NOW,
        )
        self.assertFalse(any(task.state.value == "skipped_reused" for task in plan.tasks))


if __name__ == "__main__":
    unittest.main()
