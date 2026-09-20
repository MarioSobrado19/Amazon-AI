from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
import unittest

from application.research_workspace_service import (
    CATEGORIES,
    WORKSPACE_VERSION,
    agregar_evidencia,
    crear_evidencia_manual,
    crear_research_workspace,
    eliminar_evidencia_manual,
    evaluar_research_workspace,
    exportar_workspace_json,
    exportar_workspace_txt,
    importar_workspace_json,
)


def dossier():
    return {
        "dossier_id": "dossier-001",
        "generated_at": "2026-09-20T12:00:00+00:00",
        "product": {"gtin": "629721670295"},
        "market": {
            "active_listings_observed": 2,
            "exact_gtin_matches": 2,
            "price_confidence": "low",
        },
    }


def documented(
    category, *, summary=None, observed_at=date(2026, 9, 20),
    valid_until=date(2026, 10, 1)
):
    return crear_evidencia_manual(
        category=category,
        summary=summary or f"Evidencia documentada para {category}",
        evidence_type="data",
        source_name="Fuente oficial",
        source_reference=f"https://example.org/{category}",
        observed_at=observed_at,
        valid_until=valid_until,
        confidence="medium",
        source_reviewed_by_user=True,
        limitations=("Alcance limitado a la fecha observada.",),
        created_at=datetime(2026, 9, 20, 12, tzinfo=timezone.utc),
    )


class ResearchWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
        self.workspace = crear_research_workspace(dossier(), created_at=self.now)

    def test_crea_workspace_con_evidencia_semilla_parcial(self):
        self.assertEqual(self.workspace["version"], WORKSPACE_VERSION)
        self.assertEqual(len(self.workspace["evidence"]), 3)
        self.assertEqual(self.workspace["status"], "collecting_evidence")
        self.assertFalse(self.workspace["purchase_authorized"])
        competition = next(item for item in self.workspace["coverage"] if item["category"] == "competition")
        self.assertEqual(competition["status"], "partial")
        self.assertIn("demand", self.workspace["missing_blocking_categories"])

    def test_dato_actual_revisado_se_documenta_sin_decir_verificado_por_oriva(self):
        result = agregar_evidencia(self.workspace, documented("demand"), updated_at=self.now)
        coverage = next(item for item in result["coverage"] if item["category"] == "demand")

        self.assertEqual(coverage["status"], "documented")
        self.assertIn("usuario declaró", coverage["explanation"])

    def test_dato_no_revisado_permanece_parcial(self):
        evidence = crear_evidencia_manual(
            category="demand", summary="Dato sin revisar", evidence_type="data",
            source_name="Fuente", source_reference="https://example.org/demand",
            observed_at=date(2026, 9, 20), valid_until=date(2026, 10, 1),
            confidence="medium", source_reviewed_by_user=False,
        )
        result = agregar_evidencia(self.workspace, evidence, updated_at=self.now)
        coverage = next(item for item in result["coverage"] if item["category"] == "demand")
        self.assertEqual(coverage["status"], "partial")

    def test_estimacion_y_supuesto_no_cierran_categoria(self):
        for evidence_type in ("estimate", "assumption"):
            with self.subTest(evidence_type=evidence_type):
                evidence = crear_evidencia_manual(
                    category="supplier", summary="Valor aproximado",
                    evidence_type=evidence_type, observed_at=date(2026, 9, 20),
                    confidence="low",
                )
                result = agregar_evidencia(self.workspace, evidence, updated_at=self.now)
                coverage = next(item for item in result["coverage"] if item["category"] == "supplier")
                self.assertEqual(coverage["status"], "partial")

    def test_evidencia_vencida_permanece_visible_y_marca_refresh(self):
        evidence = documented(
            "demand",
            observed_at=date(2026, 9, 18),
            valid_until=date(2026, 9, 19),
        )
        result = agregar_evidencia(self.workspace, evidence, updated_at=self.now)
        coverage = next(item for item in result["coverage"] if item["category"] == "demand")

        self.assertEqual(coverage["status"], "stale")
        self.assertEqual(result["status"], "needs_refresh")
        self.assertTrue(any(item["evidence_id"] == evidence["evidence_id"] for item in result["evidence"]))

    def test_todas_las_areas_bloqueantes_documentadas_habilitan_solo_revision(self):
        workspace = self.workspace
        for category, definition in CATEGORIES.items():
            if definition["blocking"]:
                workspace = agregar_evidencia(workspace, documented(category), updated_at=self.now)

        self.assertEqual(workspace["status"], "documented_for_review")
        self.assertTrue(workspace["documented_for_decision_review"])
        self.assertFalse(workspace["purchase_authorized"])
        self.assertEqual(workspace["missing_blocking_categories"], ())

    def test_rechaza_dato_sin_fuente_o_url_invalida(self):
        with self.assertRaisesRegex(ValueError, "nombre de la fuente"):
            crear_evidencia_manual(
                category="demand", summary="Dato", evidence_type="data",
                observed_at=date(2026, 9, 20), confidence="low",
            )
        with self.assertRaisesRegex(ValueError, "URL"):
            crear_evidencia_manual(
                category="demand", summary="Dato", evidence_type="data",
                source_name="Fuente", source_reference="nota-local",
                observed_at=date(2026, 9, 20), confidence="low",
            )

    def test_rechaza_urls_con_secretos_o_credenciales(self):
        references = (
            "https://user:password@example.org/data",
            "https://example.org/data?access_token=sensitive",
            "https://example.org/data?api_key=sensitive",
            "https://example.org/data#client_secret=sensitive",
        )
        for reference in references:
            with self.subTest(reference=reference), self.assertRaisesRegex(ValueError, "credenciales|secretos"):
                crear_evidencia_manual(
                    category="demand", summary="Dato", evidence_type="data",
                    source_name="Fuente", source_reference=reference,
                    observed_at=date(2026, 9, 20), confidence="low",
                )

    def test_no_permite_marcar_supuesto_como_fuente_revisada(self):
        with self.assertRaisesRegex(ValueError, "Solo un dato"):
            crear_evidencia_manual(
                category="costs", summary="Supuesto", evidence_type="assumption",
                observed_at=date(2026, 9, 20), confidence="low",
                source_reviewed_by_user=True,
            )

    def test_rechaza_fecha_observada_futura(self):
        with self.assertRaisesRegex(ValueError, "futuro"):
            crear_evidencia_manual(
                category="demand", summary="Dato futuro", evidence_type="data",
                source_name="Fuente", source_reference="https://example.org/future",
                observed_at=date(2026, 9, 21), valid_until=date(2026, 10, 1),
                confidence="low",
                created_at=datetime(2026, 9, 20, 12, tzinfo=timezone.utc),
            )

    def test_id_de_evidencia_es_determinista_y_no_duplica(self):
        first = documented("supplier")
        second = documented("supplier")
        self.assertEqual(first["evidence_id"], second["evidence_id"])
        once = agregar_evidencia(self.workspace, first, updated_at=self.now)
        twice = agregar_evidencia(once, second, updated_at=self.now)
        self.assertEqual(len(once["evidence"]), len(twice["evidence"]))

    def test_agregar_no_muta_workspace_original(self):
        original = deepcopy(self.workspace)
        agregar_evidencia(self.workspace, documented("supplier"), updated_at=self.now)
        self.assertEqual(self.workspace, original)

    def test_elimina_solo_evidencia_manual(self):
        evidence = documented("supplier")
        workspace = agregar_evidencia(self.workspace, evidence, updated_at=self.now)
        removed = eliminar_evidencia_manual(workspace, evidence["evidence_id"], updated_at=self.now)
        self.assertFalse(any(item["evidence_id"] == evidence["evidence_id"] for item in removed["evidence"]))
        with self.assertRaisesRegex(ValueError, "sistema"):
            eliminar_evidencia_manual(workspace, workspace["evidence"][0]["evidence_id"], updated_at=self.now)

    def test_exportacion_conserva_trazabilidad_y_no_autorizacion(self):
        export = exportar_workspace_json(self.workspace)
        text_export = exportar_workspace_txt(self.workspace)
        decoded = json.loads(export["contenido"])
        self.assertEqual(decoded["workspace_id"], self.workspace["workspace_id"])
        self.assertFalse(decoded["purchase_authorized"])
        self.assertIn("warnings", decoded)
        self.assertIn("COBERTURA", text_export["contenido"].decode())
        self.assertIn("no autoriza comprar", text_export["contenido"].decode())

    def test_fechas_sin_timezone_se_rechazan_en_evaluacion(self):
        with self.assertRaisesRegex(ValueError, "zona horaria"):
            evaluar_research_workspace(self.workspace, assessed_at=datetime(2026, 9, 20))

    def test_exportar_e_importar_restaura_solo_evidencia_manual(self):
        evidence = documented("supplier")
        source = agregar_evidencia(self.workspace, evidence, updated_at=self.now)
        export = exportar_workspace_json(source)
        restored = importar_workspace_json(
            export["contenido"], self.workspace, imported_at=self.now
        )

        self.assertTrue(any(item["evidence_id"] == evidence["evidence_id"] for item in restored["evidence"]))
        system = [item for item in restored["evidence"] if item["origin"].startswith("system")]
        self.assertEqual(len(system), 3)

    def test_importacion_rechaza_otro_expediente_json_invalido_y_archivo_grande(self):
        export = exportar_workspace_json(self.workspace)
        payload = json.loads(export["contenido"])
        payload["dossier_id"] = "otro-expediente"
        with self.assertRaisesRegex(ValueError, "otro expediente"):
            importar_workspace_json(json.dumps(payload), self.workspace, imported_at=self.now)
        with self.assertRaisesRegex(ValueError, "JSON válido"):
            importar_workspace_json(b"{", self.workspace, imported_at=self.now)
        with self.assertRaisesRegex(ValueError, "demasiado grande"):
            importar_workspace_json(b"x" * 1_000_001, self.workspace, imported_at=self.now)

    def test_importacion_detecta_evidencia_manual_modificada(self):
        evidence = documented("supplier")
        source = agregar_evidencia(self.workspace, evidence, updated_at=self.now)
        payload = json.loads(exportar_workspace_json(source)["contenido"])
        manual = next(item for item in payload["evidence"] if item["origin"] == "user_declared")
        manual["summary"] = "Contenido alterado"

        with self.assertRaisesRegex(ValueError, "modificada|corrupta"):
            importar_workspace_json(json.dumps(payload), self.workspace, imported_at=self.now)


if __name__ == "__main__":
    unittest.main()
