import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path

from application.marketplace_service import (
    MARKETPLACE_ENGINE_VERSION,
    crear_catalogo_marketplace,
)
from application.ports import MarketplaceAdapterTimeout, MarketplaceAdapterUnavailable
from domain.contracts import MarketplaceCatalogIssue, MarketplaceCatalogResult
from domain.entities import BusinessModel, Marketplace, MarketplaceConditionSnapshot
from domain.enums import (
    ConfidenceLevel,
    FreshnessStatus,
    OperationalLoad,
    VerificationStatus,
)
from domain.value_objects import Region
from tests.fakes.marketplace_adapter import FakeMarketplaceAdapter


NOW = datetime(2026, 8, 9, 12, tzinfo=timezone.utc)
REGION = Region("US")
MARKETPLACE_ID = "10000000-0000-4000-8000-000000000001"
MODEL_ONE_ID = "20000000-0000-4000-8000-000000000001"
MODEL_TWO_ID = "20000000-0000-4000-8000-000000000002"
SNAPSHOT_ONE_ID = "30000000-0000-4000-8000-000000000001"
SNAPSHOT_TWO_ID = "30000000-0000-4000-8000-000000000002"


def marketplace(**overrides):
    values = {
        "marketplace_id": MARKETPLACE_ID,
        "name": "Marketplace Demo",
        "region": REGION,
        "currency": "USD",
        "source": "Fuente demo verificable",
        "valid_from": NOW,
        "version": "catalog/1",
        "capabilities": ("venta digital",),
        "general_requirements": ("registro válido",),
        "general_restrictions": ("producto permitido",),
        "confidence": ConfidenceLevel.HIGH,
    }
    values.update(overrides)
    return Marketplace(**values)


def model(model_id=MODEL_ONE_ID, name="Operación directa", **overrides):
    values = {
        "business_model_id": model_id,
        "name": name,
        "region": REGION,
        "marketplace_id": MARKETPLACE_ID,
        "confidence": ConfidenceLevel.HIGH,
        "version": "model/1",
        "requirements": ("capacidad operativa",),
        "restrictions": ("límite operativo",),
        "advantages": ("control operativo",),
        "risks": ("variación logística",),
        "operational_load": OperationalLoad.MEDIUM,
        "source": "Fuente demo de modelos",
        "valid_from": NOW,
        "represents_external_conditions": True,
    }
    values.update(overrides)
    return BusinessModel(**values)


def snapshot(
    snapshot_id=SNAPSHOT_ONE_ID,
    freshness=FreshnessStatus.CURRENT,
    condition_type="tarifa_demo",
    **overrides,
):
    values = {
        "snapshot_id": snapshot_id,
        "marketplace": marketplace(),
        "region": REGION,
        "condition_type": condition_type,
        "values": {"importe": "4.00", "detalle": {"unidad": "artículo"}},
        "source": "Fuente demo de condiciones",
        "consulted_at": NOW,
        "effective_at": NOW,
        "expires_at": NOW + timedelta(days=30),
        "freshness": freshness,
        "confidence": ConfidenceLevel.HIGH,
        "verification_status": VerificationStatus.VERIFIED,
        "version": "snapshot/1",
    }
    values.update(overrides)
    return MarketplaceConditionSnapshot(**values)


def adapter(**overrides):
    values = {
        "marketplace": marketplace(),
        "business_models": (
            model(),
            model(MODEL_TWO_ID, "Operación delegada"),
        ),
        "snapshots": (
            snapshot(),
            snapshot(
                SNAPSHOT_TWO_ID,
                condition_type="requisito_demo",
            ),
        ),
        "requirements": ("identidad confirmada",),
        "restrictions": ("región compatible",),
        "capabilities": ("catálogo normalizado",),
    }
    values.update(overrides)
    return FakeMarketplaceAdapter(**values)


class MarketplaceServiceTests(unittest.TestCase):
    def test_catalogo_valido_con_multiples_modelos_y_snapshots(self):
        result = crear_catalogo_marketplace(adapter(), REGION, generated_at=NOW)

        self.assertIsInstance(result, MarketplaceCatalogResult)
        self.assertEqual(result.version, MARKETPLACE_ENGINE_VERSION)
        self.assertEqual(len(result.marketplaces), 1)
        self.assertEqual(len(result.business_models), 2)
        self.assertEqual(len(result.snapshots), 2)
        self.assertEqual(result.confidence, ConfidenceLevel.HIGH)
        self.assertEqual(result.functional_errors, ())

    def test_catalogo_consolida_requisitos_restricciones_y_capacidades(self):
        result = crear_catalogo_marketplace(adapter(), REGION, generated_at=NOW)

        self.assertEqual(
            result.requirements,
            ("registro válido", "identidad confirmada", "capacidad operativa"),
        )
        self.assertEqual(
            result.restrictions,
            ("producto permitido", "región compatible", "límite operativo"),
        )
        self.assertEqual(
            result.capabilities, ("venta digital", "catálogo normalizado")
        )

    def test_freshness_vigente_queda_contabilizado(self):
        result = crear_catalogo_marketplace(adapter(), REGION, generated_at=NOW)
        summary = result.freshness_summary.to_dict()

        self.assertEqual(summary[FreshnessStatus.CURRENT.value], 2)
        self.assertEqual(summary[FreshnessStatus.EXPIRED.value], 0)
        self.assertFalse(result.warnings)

    def test_snapshot_expirado_se_conserva_y_reduce_confianza(self):
        expired = snapshot(
            freshness=FreshnessStatus.EXPIRED,
            expires_at=NOW + timedelta(days=1),
        )
        result = crear_catalogo_marketplace(
            adapter(snapshots=(expired,)), REGION, generated_at=NOW
        )

        self.assertEqual(result.snapshots, (expired,))
        self.assertEqual(result.confidence, ConfidenceLevel.LOW)
        self.assertIn("expiradas", " ".join(result.warnings))

    def test_snapshots_vigente_y_expirado_permanecen_visibles(self):
        current = snapshot()
        expired = snapshot(
            SNAPSHOT_TWO_ID,
            freshness=FreshnessStatus.EXPIRED,
            expires_at=NOW + timedelta(days=1),
        )
        result = crear_catalogo_marketplace(
            adapter(snapshots=(current, expired)), REGION, generated_at=NOW
        )

        self.assertEqual(result.snapshots, (current, expired))
        self.assertEqual(result.freshness_summary.to_dict()["vigente"], 1)
        self.assertEqual(result.freshness_summary.to_dict()["expirada"], 1)
        self.assertEqual(result.confidence, ConfidenceLevel.LOW)
        self.assertIn("expiradas", " ".join(result.warnings))

    def test_freshness_proxima_a_expirar_reduce_confianza_a_media(self):
        expiring = snapshot(freshness=FreshnessStatus.EXPIRING)
        result = crear_catalogo_marketplace(
            adapter(snapshots=(expiring,)), REGION, generated_at=NOW
        )

        self.assertEqual(result.confidence, ConfidenceLevel.MEDIUM)
        self.assertIn("próximas a expirar", " ".join(result.warnings))

    def test_freshness_desconocida_es_explicita(self):
        unknown = snapshot(freshness=FreshnessStatus.UNKNOWN)
        result = crear_catalogo_marketplace(
            adapter(snapshots=(unknown,)), REGION, generated_at=NOW
        )

        self.assertEqual(result.confidence, ConfidenceLevel.LOW)
        self.assertIn("vigencia desconocida", " ".join(result.warnings))

    def test_adaptador_sin_marketplace_no_inventa_sustituto(self):
        result = crear_catalogo_marketplace(
            FakeMarketplaceAdapter(), REGION, generated_at=NOW
        )

        self.assertEqual(result.marketplaces, ())
        self.assertEqual(result.business_models, ())
        self.assertEqual(result.snapshots, ())
        self.assertIn("marketplace", result.missing_data)
        self.assertEqual(result.confidence, ConfidenceLevel.LOW)

    def test_fuente_sin_modelos_ni_condiciones_declara_vacios(self):
        result = crear_catalogo_marketplace(
            adapter(business_models=(), snapshots=()), REGION, generated_at=NOW
        )

        self.assertIn("business_models", result.missing_data)
        self.assertIn("condition_snapshots", result.missing_data)
        self.assertIn("No hay modelos", " ".join(result.warnings))
        self.assertIn("No hay condiciones", " ".join(result.warnings))
        self.assertEqual(result.confidence, ConfidenceLevel.LOW)

    def test_adaptador_no_disponible_produce_error_funcional(self):
        result = crear_catalogo_marketplace(
            FakeMarketplaceAdapter(
                failures={"marketplace": MarketplaceAdapterUnavailable("sin conexión")}
            ),
            REGION,
            generated_at=NOW,
        )

        self.assertEqual(result.marketplaces, ())
        self.assertEqual(result.functional_errors[0].code, "adapter_unavailable")
        self.assertTrue(result.functional_errors[0].retryable)
        self.assertNotIn("sin conexión", result.to_dict()["marketplaces"])

    def test_timeout_de_snapshots_conserva_catalogo_parcial(self):
        result = crear_catalogo_marketplace(
            adapter(failures={"snapshots": MarketplaceAdapterTimeout("agotado")}),
            REGION,
            generated_at=NOW,
        )

        self.assertEqual(len(result.business_models), 2)
        self.assertEqual(result.snapshots, ())
        self.assertIn("condition_snapshots", result.missing_data)
        self.assertEqual(result.functional_errors[0].code, "adapter_timeout")
        self.assertEqual(result.confidence, ConfidenceLevel.LOW)

    def test_multiples_errores_conservan_datos_recuperados_previamente(self):
        result = crear_catalogo_marketplace(
            adapter(
                failures={
                    "snapshots": MarketplaceAdapterTimeout("agotado"),
                    "restrictions": MarketplaceAdapterUnavailable("sin fuente"),
                }
            ),
            REGION,
            generated_at=NOW,
        )

        self.assertEqual(result.marketplaces, (marketplace(),))
        self.assertEqual(len(result.business_models), 2)
        self.assertEqual(result.requirements[0], "registro válido")
        self.assertEqual(result.capabilities[-1], "catálogo normalizado")
        self.assertEqual(
            tuple(issue.code for issue in result.functional_errors),
            ("adapter_timeout", "adapter_unavailable"),
        )
        self.assertTrue(all(issue.retryable for issue in result.functional_errors))

    def test_region_incompatible_no_expone_catalogo_como_disponible(self):
        other_region = Region("CA")
        result = crear_catalogo_marketplace(
            FakeMarketplaceAdapter(marketplace=marketplace()),
            other_region,
            generated_at=NOW,
        )

        self.assertEqual(result.marketplaces, ())
        self.assertIn("compatible_marketplace_region", result.missing_data)
        self.assertIn("no es compatible", result.unavailable_reasons[0])
        self.assertEqual(result.functional_errors[0].code, "incompatible_region")
        self.assertFalse(result.functional_errors[0].retryable)

    def test_modelo_incompatible_se_omite_con_advertencia(self):
        foreign_marketplace_id = "10000000-0000-4000-8000-000000000099"
        incompatible = model(marketplace_id=foreign_marketplace_id)
        result = crear_catalogo_marketplace(
            adapter(business_models=(model(), incompatible)),
            REGION,
            generated_at=NOW,
        )

        self.assertEqual(result.business_models, (model(),))
        self.assertIn("compatible_business_models", result.missing_data)
        self.assertIn("incompatibles", " ".join(result.warnings))

    def test_trazabilidad_completa_y_serializacion_estable(self):
        result = crear_catalogo_marketplace(adapter(), REGION, generated_at=NOW)
        serialized = result.to_dict()

        self.assertEqual(serialized["generated_at"], NOW.isoformat())
        self.assertIn("fake-marketplace-adapter", serialized["sources"])
        self.assertIn("Fuente demo verificable", serialized["sources"])
        self.assertEqual(serialized["snapshots"][0]["source"], "Fuente demo de condiciones")
        self.assertEqual(serialized["snapshots"][0]["version"], "snapshot/1")
        self.assertEqual(serialized["snapshots"][0]["freshness"], "vigente")
        json.dumps(serialized, ensure_ascii=False)

    def test_contrato_anterior_sigue_siendo_compatible(self):
        legacy_shape = MarketplaceCatalogResult("catalog-1", "1", NOW)
        self.assertEqual(legacy_shape.marketplaces, ())
        self.assertEqual(legacy_shape.functional_errors, ())
        self.assertEqual(legacy_shape.freshness_summary.to_dict(), {})

    def test_colecciones_y_serializacion_no_exponen_mutabilidad(self):
        result = crear_catalogo_marketplace(adapter(), REGION, generated_at=NOW)
        serialized = result.to_dict()
        serialized["warnings"].append("mutación externa")
        serialized["freshness_summary"]["vigente"] = 999

        self.assertIsInstance(result.business_models, tuple)
        self.assertIsInstance(result.functional_errors, tuple)
        self.assertNotIn("mutación externa", result.warnings)
        self.assertEqual(result.freshness_summary.to_dict()["vigente"], 2)
        with self.assertRaises(FrozenInstanceError):
            result.warnings = ("cambio",)

    def test_issue_es_inmutable_y_serializable(self):
        issue = MarketplaceCatalogIssue("partial", "Información parcial", "fake", True)
        self.assertEqual(
            issue.to_dict(),
            {
                "code": "partial",
                "message": "Información parcial",
                "source": "fake",
                "retryable": True,
            },
        )


class MarketplaceArchitectureTests(unittest.TestCase):
    def test_motor_y_puerto_no_contienen_reglas_de_marketplaces_reales(self):
        root = Path(__file__).parents[1]
        paths = (
            root / "application" / "marketplace_service.py",
            root / "application" / "ports" / "marketplace_adapter.py",
            root / "domain" / "contracts" / "marketplace_catalog_result.py",
            root / "domain" / "contracts" / "marketplace_catalog_issue.py",
        )
        source = "\n".join(path.read_text(encoding="utf-8") for path in paths).casefold()
        for forbidden in ("amazon", "fba", "fbm", "wfs", "streamlit"):
            self.assertNotIn(forbidden, source)

    def test_fake_adapter_vive_solo_en_tests(self):
        root = Path(__file__).parents[1]
        production = list((root / "application").rglob("*fake*"))
        self.assertEqual(production, [])


if __name__ == "__main__":
    unittest.main()
