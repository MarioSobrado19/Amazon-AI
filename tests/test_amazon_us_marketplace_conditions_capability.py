import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from urllib.request import Request

from application.research_models import (
    ResearchCapabilityRequest,
    ResearchCapabilityResultStatus,
    ResearchExecutionContext,
)
from application.research_orchestration_service import (
    create_research_plan,
    execute_research_plan,
)
from domain.enums import (
    EvidenceType,
    FreshnessStatus,
    ResearchCategory,
    ResearchQuestionStatus,
    VerificationStatus,
)
from domain.value_objects import Region, ResearchNeed, ResearchQuestion
from infrastructure.amazon_us.marketplace_conditions_capability import (
    AmazonUSMarketplaceConditionsCapability,
    SOURCE_URL,
    SourceAcquisitionError,
    SourceDocument,
    _OfficialRedirectHandler,
    parse_selling_plan_fees,
)
from tests.test_research_foundation import assess


NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
OFFICIAL_HTML = """
<html><head><script>Professional $1.00 / month</script></head><body>
  <h3>Individual</h3><div><sup>$</sup>0.99</div><span>/ item sold</span>
  <h3>Professional</h3><div>$39.99</div><span>/ month</span>
</body></html>
"""


def request(**changes):
    values = {
        "task_id": "task-1",
        "category": ResearchCategory.MARKETPLACE,
        "question": "¿Cuáles son las tarifas base de los planes de venta?",
        "subject_type": "business_path",
        "subject_id": "path-1",
        "execution_context": ResearchExecutionContext("project-a", "request-1", NOW, Region("US")),
        "region": Region("US"),
        "marketplace_id": "amazon-us",
    }
    values.update(changes)
    return ResearchCapabilityRequest(**values)


def document(html=OFFICIAL_HTML, url=SOURCE_URL):
    return SourceDocument(html, url, NOW)


class AmazonUSMarketplaceConditionsTests(unittest.TestCase):
    def test_parser_extrae_ambos_planes(self):
        values = parse_selling_plan_fees(OFFICIAL_HTML)
        self.assertEqual(values["individual"]["amount"], "0.99")
        self.assertEqual(values["professional"]["amount"], "39.99")
        self.assertEqual(values["currency"], "USD")

    def test_cambios_html_irrelevantes_conservan_semantica(self):
        changed = """
        <html><body><main><section class='new-layout'>
        <h2>Individual</h2><strong>$ 0.99</strong><em>per item sold</em>
        </section><aside>Información adicional</aside><section>
        <h2>Professional</h2><strong>$ 39.99</strong><em>per month</em>
        </section></main></body></html>
        """
        self.assertEqual(parse_selling_plan_fees(changed), parse_selling_plan_fees(OFFICIAL_HTML))

    def test_parser_falla_cerrado_si_falta_un_plan(self):
        with self.assertRaises(SourceAcquisitionError) as caught:
            parse_selling_plan_fees("<h3>Individual</h3>$0.99 / item sold")
        self.assertEqual(caught.exception.code, "source_format_changed")

    def test_parser_falla_si_falta_individual(self):
        with self.assertRaises(SourceAcquisitionError):
            parse_selling_plan_fees("Professional $39.99 / month")

    def test_parser_falla_si_falta_professional(self):
        with self.assertRaises(SourceAcquisitionError):
            parse_selling_plan_fees("Individual $0.99 / item sold")

    def test_parser_falla_si_faltan_ambas(self):
        with self.assertRaises(SourceAcquisitionError):
            parse_selling_plan_fees("Pricing information")

    def test_parser_rechaza_precio_duplicado_ambiguo(self):
        duplicated = OFFICIAL_HTML.replace("</body>", "<p>Individual $1.25 per item sold</p></body>")
        with self.assertRaises(SourceAcquisitionError):
            parse_selling_plan_fees(duplicated)

    def test_parser_rechaza_moneda_inesperada(self):
        with self.assertRaises(SourceAcquisitionError):
            parse_selling_plan_fees("Individual €0.99 / item sold Professional €39.99 / month")

    def test_parser_rechaza_contenido_vacio(self):
        with self.assertRaises(SourceAcquisitionError):
            parse_selling_plan_fees("")

    def test_pagina_de_error_http_200_no_se_parsea(self):
        error_page = "<h1>Service unavailable</h1> Individual $0.99 / item sold Professional $39.99 / month"
        with self.assertRaises(SourceAcquisitionError):
            parse_selling_plan_fees(error_page)

    def test_redirect_interno_https_permitido(self):
        redirected = _OfficialRedirectHandler().redirect_request(
            Request(SOURCE_URL), None, 302, "Found", {},
            "https://sell.amazon.com/pricing/new-location",
        )
        self.assertEqual(redirected.full_url, "https://sell.amazon.com/pricing/new-location")

    def test_redirect_externo_rechazado_antes_de_aceptar_contenido(self):
        with self.assertRaises(SourceAcquisitionError) as caught:
            _OfficialRedirectHandler().redirect_request(
                Request(SOURCE_URL), None, 302, "Found", {},
                "https://mirror.example/pricing",
            )
        self.assertEqual(caught.exception.code, "unexpected_redirect")

    def test_redirect_con_credenciales_embebidas_se_rechaza(self):
        with self.assertRaises(SourceAcquisitionError):
            _OfficialRedirectHandler().redirect_request(
                Request(SOURCE_URL), None, 302, "Found", {},
                "https://user:secret@sell.amazon.com/pricing",
            )

    def test_redirect_con_puerto_no_estandar_se_rechaza(self):
        with self.assertRaises(SourceAcquisitionError):
            _OfficialRedirectHandler().redirect_request(
                Request(SOURCE_URL), None, 302, "Found", {},
                "https://sell.amazon.com:8443/pricing",
            )

    def test_admite_solo_marketplace_amazon_us_publico(self):
        capability = AmazonUSMarketplaceConditionsCapability(lambda: document())
        self.assertTrue(capability.can_handle(request()))
        self.assertFalse(capability.can_handle(request(marketplace_id="other")))
        self.assertFalse(capability.can_handle(request(region=Region("CA"))))
        self.assertFalse(capability.can_handle(request(category=ResearchCategory.DEMAND)))

    def test_produce_evidencia_verificada_vigente_y_trazable(self):
        result = AmazonUSMarketplaceConditionsCapability(lambda: document()).execute(request())
        self.assertIs(result.status, ResearchCapabilityResultStatus.SUCCESS)
        self.assertEqual(len(result.evidence), 1)
        evidence = result.evidence[0]
        self.assertIs(evidence.verification_status, VerificationStatus.VERIFIED)
        self.assertIs(evidence.freshness, FreshnessStatus.CURRENT)
        self.assertEqual(evidence.source_reference, SOURCE_URL)
        self.assertEqual(evidence.marketplace_id, "amazon-us")
        self.assertEqual(evidence.value.to_dict()["professional"]["amount"], "39.99")
        self.assertIn("content_sha256", evidence.value.to_dict())
        self.assertTrue(evidence.limitations)

    def test_documento_idempotente_en_la_misma_recuperacion(self):
        capability = AmazonUSMarketplaceConditionsCapability(lambda: document())
        first = capability.execute(request()).evidence[0]
        second = capability.execute(request()).evidence[0]
        self.assertEqual(first.evidence_id, second.evidence_id)

    def test_huella_semantica_ignora_cambio_visual(self):
        alternate = OFFICIAL_HTML.replace("<body>", "<body><div>Diseño actualizado</div>")
        first = AmazonUSMarketplaceConditionsCapability(lambda: document()).execute(request()).evidence[0]
        second = AmazonUSMarketplaceConditionsCapability(lambda: document(alternate)).execute(request()).evidence[0]
        self.assertEqual(first.value.to_dict()["content_sha256"], second.value.to_dict()["content_sha256"])

    def test_consultas_historicas_distintas_conservan_ids_propios(self):
        first_document = document()
        second_document = SourceDocument(OFFICIAL_HTML, SOURCE_URL, NOW + timedelta(days=1))
        first = AmazonUSMarketplaceConditionsCapability(lambda: first_document).execute(request()).evidence[0]
        second = AmazonUSMarketplaceConditionsCapability(lambda: second_document).execute(request()).evidence[0]
        self.assertEqual(first.value.to_dict()["content_sha256"], second.value.to_dict()["content_sha256"])
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_rechaza_documento_fuera_del_dominio_oficial(self):
        result = AmazonUSMarketplaceConditionsCapability(
            lambda: document(url="https://example.com/pricing")
        ).execute(request())
        self.assertIs(result.status, ResearchCapabilityResultStatus.FAILED)
        self.assertEqual(result.failure.code, "untrusted_source")
        self.assertFalse(result.evidence)

    def test_timeout_permanece_fallo_y_no_evidencia(self):
        def timeout():
            raise SourceAcquisitionError("timeout", "La fuente no respondió.", retryable=True)

        result = AmazonUSMarketplaceConditionsCapability(timeout).execute(request())
        self.assertIs(result.status, ResearchCapabilityResultStatus.FAILED)
        self.assertEqual(result.failure.code, "timeout")
        self.assertTrue(result.failure.retryable)
        self.assertFalse(result.evidence)

    def test_cambio_de_formato_no_inventa_datos(self):
        result = AmazonUSMarketplaceConditionsCapability(
            lambda: document("<html>Pricing temporarily unavailable</html>")
        ).execute(request())
        self.assertIs(result.status, ResearchCapabilityResultStatus.FAILED)
        self.assertEqual(result.failure.code, "source_format_changed")
        self.assertFalse(result.evidence)

    def test_request_incompatible_falla_explicitamente(self):
        result = AmazonUSMarketplaceConditionsCapability(lambda: document()).execute(
            request(marketplace_id="other")
        )
        self.assertIs(result.status, ResearchCapabilityResultStatus.FAILED)
        self.assertEqual(result.failure.code, "unsupported_request")

    def test_vertical_orchestrator_fuente_evidencia_assessment(self):
        baseline = assess()
        subject_id = baseline.investigation.subject_id
        need = ResearchNeed(
            "business_path", subject_id, ResearchCategory.MARKETPLACE,
            "Faltan las tarifas base del marketplace.", "high", True,
            (EvidenceType.DATA,), missing_information=("tarifas base",),
        )
        question = ResearchQuestion(
            need.need_id, "¿Cuáles son las tarifas base de los planes de venta?",
            "business_path", subject_id, (EvidenceType.DATA,),
            ResearchQuestionStatus.PENDING, Region("US"), "amazon-us",
        )
        marketplace_assessment = replace(
            baseline, needs=(need,), questions=(question,), evidence=(), findings=(), conflicts=(),
        )
        capability = AmazonUSMarketplaceConditionsCapability(lambda: document())
        context = request().execution_context
        plan = create_research_plan(
            assessment=marketplace_assessment,
            capabilities=(capability,),
            execution_context=context,
            created_at=NOW,
        )
        result = execute_research_plan(
            plan=plan,
            assessment=marketplace_assessment,
            capabilities=(capability,),
            execution_context=context,
            generated_at=NOW,
        )
        self.assertEqual(len(result.completed_tasks), 1)
        self.assertEqual(len(result.evidence_obtained), 1)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.coverage[0].status.value, "covered")


if __name__ == "__main__":
    unittest.main()
