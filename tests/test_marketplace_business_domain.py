import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from domain.contracts import (
    BusinessModelAssessment,
    MarketplaceCatalogResult,
    OpportunityScenarioResult,
)
from domain.entities import (
    BusinessModel,
    Marketplace,
    MarketplaceConditionSnapshot,
    Opportunity,
    OpportunityScenario,
    Product,
    Result,
)
from domain.enums import (
    ConfidenceLevel,
    EvidenceType,
    FreshnessStatus,
    OperationalLoad,
    VerificationStatus,
)
from domain.exceptions import DomainValidationError
from domain.value_objects import FrozenMapping, Region
from domain.entities._identity import new_internal_id


NOW = datetime(2026, 8, 8, 12, tzinfo=timezone.utc)
MARKETPLACE_ID = "11111111-1111-4111-8111-111111111111"
BUSINESS_MODEL_ID = "22222222-2222-4222-8222-222222222222"
SNAPSHOT_ID = "33333333-3333-4333-8333-333333333333"
SCENARIO_ID = "44444444-4444-4444-8444-444444444444"


def marketplace(**overrides):
    values = {
        "marketplace_id": MARKETPLACE_ID,
        "name": "Canal Demo",
        "region": Region("US"),
        "currency": "usd",
        "source": "Catálogo verificable",
        "valid_from": NOW,
        "version": "1",
        "categories": ("hogar",),
        "capabilities": ("venta en línea",),
    }
    values.update(overrides)
    return Marketplace(**values)


def business_model(**overrides):
    values = {
        "business_model_id": BUSINESS_MODEL_ID,
        "name": "Operación delegada genérica",
        "description": "El canal asume parte de la operación.",
        "marketplace_id": MARKETPLACE_ID,
        "region": Region("US"),
        "seller_responsibilities": ("Preparar inventario",),
        "marketplace_responsibilities": ("Procesar entregas",),
        "requirements": ("Cuenta verificada",),
        "restrictions": ("Categorías sujetas a aprobación",),
        "advantages": ("Menor carga logística directa",),
        "disadvantages": ("Mayor dependencia del canal",),
        "risks": ("Cambios en condiciones externas",),
        "operational_load": OperationalLoad.MEDIUM,
        "source": "Catálogo verificable",
        "valid_from": NOW,
        "confidence": ConfidenceLevel.MEDIUM,
        "version": "1",
        "represents_external_conditions": True,
    }
    values.update(overrides)
    return BusinessModel(**values)


def snapshot(snapshot_id=SNAPSHOT_ID, value="10.00", **overrides):
    values = {
        "snapshot_id": snapshot_id,
        "marketplace": marketplace(),
        "region": Region("US"),
        "condition_type": "tarifa",
        "values": {"importe": value, "moneda": "USD"},
        "source": "Documento oficial verificable",
        "consulted_at": NOW,
        "effective_at": NOW,
        "expires_at": NOW + timedelta(days=30),
        "freshness": FreshnessStatus.CURRENT,
        "confidence": ConfidenceLevel.HIGH,
        "verification_status": VerificationStatus.VERIFIED,
        "version": "1",
    }
    values.update(overrides)
    return MarketplaceConditionSnapshot(**values)


def opportunity():
    return Opportunity("opp-1", Product("product-1", "Producto demo"))


def result(result_id="result-1", evidence_type=EvidenceType.ESTIMATE):
    return Result(
        result_id=result_id,
        name="costo_estimado",
        value="10.00",
        evidence_type=evidence_type,
        source="Motor existente",
        confidence=ConfidenceLevel.MEDIUM,
        recorded_at=NOW,
        version="1",
    )


def scenario(scenario_id=SCENARIO_ID, model=None, **overrides):
    values = {
        "scenario_id": scenario_id,
        "opportunity": opportunity(),
        "marketplace": marketplace(),
        "business_model": model or business_model(),
        "region": Region("US"),
        "evaluated_at": NOW,
        "conditions": (snapshot(),),
        "costs": (result(),),
        "assumptions": (result("assumption-1", EvidenceType.ASSUMPTION),),
    }
    values.update(overrides)
    return OpportunityScenario(**values)


class RegionAndImmutableDataTests(unittest.TestCase):
    def test_region_compara_por_valor_y_normaliza(self):
        self.assertEqual(Region("us", " New York "), Region("US", "New York"))
        self.assertEqual(Region("us").to_dict(), {"country_code": "US", "area": None})

    def test_region_es_inmutable_y_rechaza_pais_invalido(self):
        region = Region("US")
        with self.assertRaises(FrozenInstanceError):
            region.area = "NY"
        with self.assertRaises(DomainValidationError):
            Region("USA")

    def test_frozen_mapping_conserva_estructura_sin_exponer_mutabilidad(self):
        source = {"tarifa": {"tramos": [1, 2]}}
        frozen = FrozenMapping.from_mapping(source)
        source["tarifa"]["tramos"].append(3)
        serialized = frozen.to_dict()
        serialized["tarifa"]["tramos"].append(9)

        self.assertEqual(frozen.to_dict(), {"tarifa": {"tramos": [1, 2]}})
        self.assertEqual(frozen, FrozenMapping.from_mapping({"tarifa": {"tramos": [1, 2]}}))

    def test_frozen_mapping_anidado_compara_por_contenido_no_por_orden(self):
        first = FrozenMapping.from_mapping(
            {"costos": {"envio": 3, "tarifa": 5}, "tramos": [1, {"tope": 2}]}
        )
        second = FrozenMapping.from_mapping(
            {"tramos": [1, {"tope": 2}], "costos": {"tarifa": 5, "envio": 3}}
        )
        self.assertEqual(first, second)


class BusinessModelTests(unittest.TestCase):
    def test_creacion_completa_y_serializacion(self):
        model = business_model()
        data = model.to_dict()

        self.assertEqual(data["name"], "Operación delegada genérica")
        self.assertEqual(data["operational_load"], "media")
        self.assertEqual(data["region"]["country_code"], "US")
        self.assertEqual(data["valid_from"], NOW.isoformat())

    def test_marketplace_es_opcional_sin_condiciones_externas(self):
        model = business_model(
            marketplace_id=None,
            requirements=(),
            restrictions=(),
            source=None,
            valid_from=None,
            represents_external_conditions=False,
        )
        self.assertIsNone(model.marketplace_id)

    def test_nombre_es_obligatorio(self):
        with self.assertRaises(DomainValidationError):
            business_model(name=" ")

    def test_condiciones_externas_requieren_fuente_y_vigencia(self):
        with self.assertRaisesRegex(DomainValidationError, "source y valid_from"):
            business_model(source=None)
        with self.assertRaisesRegex(DomainValidationError, "source y valid_from"):
            business_model(valid_from=None)

    def test_identidad_y_colecciones_inmutables(self):
        first = business_model(name="Nombre A")
        same_identity = business_model(name="Nombre B")
        self.assertEqual(first, same_identity)
        self.assertIsInstance(first.requirements, tuple)
        with self.assertRaises(FrozenInstanceError):
            first.name = "Otro"

    def test_identidad_interna_no_deriva_del_nombre_ni_acepta_id_externo(self):
        self.assertEqual(business_model(name="A"), business_model(name="B"))
        with self.assertRaisesRegex(DomainValidationError, "ID externo"):
            business_model(business_model_id="programa-del-canal")


class MarketplaceTests(unittest.TestCase):
    def test_crea_marketplace_generico(self):
        item = marketplace()
        self.assertEqual(item.currency, "USD")
        self.assertEqual(item.to_dict()["categories"], ["hogar"])

    def test_nombre_region_moneda_fuente_y_vigencia_son_validos(self):
        invalid_values = (
            {"name": ""},
            {"region": object()},
            {"currency": "US"},
            {"source": ""},
            {"valid_from": datetime(2026, 8, 8)},
        )
        for overrides in invalid_values:
            with self.subTest(overrides=overrides), self.assertRaises(DomainValidationError):
                marketplace(**overrides)

    def test_identidad_depende_de_marketplace_id(self):
        self.assertEqual(marketplace(name="A"), marketplace(name="B"))

    def test_generador_produce_ids_internos_unicos_y_canonicos(self):
        first = new_internal_id()
        second = new_internal_id()
        self.assertNotEqual(first, second)
        self.assertEqual(str(UUID(first)), first)
        self.assertEqual(str(UUID(second)), second)

    def test_marketplace_rechaza_referencia_externa_como_identidad(self):
        with self.assertRaisesRegex(DomainValidationError, "ID externo"):
            marketplace(marketplace_id="canal-externo-123")


class SnapshotTests(unittest.TestCase):
    def test_conserva_metadatos_timezone_y_version(self):
        item = snapshot()
        data = item.to_dict()

        self.assertEqual(data["source"], "Documento oficial verificable")
        self.assertEqual(data["freshness"], "vigente")
        self.assertEqual(data["verification_status"], "verificada")
        self.assertEqual(data["version"], "1")
        self.assertTrue(data["consulted_at"].endswith("+00:00"))

    def test_rechaza_fecha_sin_timezone_fuente_o_version_vacias(self):
        invalid_values = (
            {"consulted_at": datetime(2026, 8, 8)},
            {"effective_at": datetime(2026, 8, 8)},
            {"source": ""},
            {"version": ""},
        )
        for overrides in invalid_values:
            with self.subTest(overrides=overrides), self.assertRaises(DomainValidationError):
                snapshot(**overrides)

    def test_snapshots_historicos_son_independientes(self):
        old = snapshot("99999999-9999-4999-8999-999999999999", "10.00")
        new = snapshot("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "12.00")

        self.assertNotEqual(old, new)
        self.assertEqual(old.values.to_dict()["importe"], "10.00")
        self.assertEqual(new.values.to_dict()["importe"], "12.00")
        with self.assertRaises(FrozenInstanceError):
            old.version = "2"


class OpportunityScenarioTests(unittest.TestCase):
    def test_referencia_oportunidad_sin_mutarla_y_conserva_contexto(self):
        original = opportunity()
        before = original.to_dict()
        item = scenario(opportunity=original, supplier_id="supplier-1")

        self.assertIs(item.opportunity, original)
        self.assertEqual(original.to_dict(), before)
        self.assertEqual(item.supplier_id, "supplier-1")
        self.assertEqual(item.to_dict()["conditions"][0]["snapshot_id"], SNAPSHOT_ID)

    def test_dos_escenarios_distintos_comparten_oportunidad(self):
        shared = opportunity()
        first = scenario("55555555-5555-4555-8555-555555555555", opportunity=shared)
        second = scenario(
            "66666666-6666-4666-8666-666666666666",
            opportunity=shared,
            model=business_model(
                business_model_id="77777777-7777-4777-8777-777777777777",
                name="Operación directa",
            ),
        )

        self.assertNotEqual(first, second)
        self.assertIs(first.opportunity, second.opportunity)

    def test_requiere_oportunidad_y_contexto_coherente(self):
        with self.assertRaises(DomainValidationError):
            scenario(opportunity=object())
        with self.assertRaisesRegex(DomainValidationError, "otro marketplace"):
            scenario(
                model=business_model(
                    marketplace_id="88888888-8888-4888-8888-888888888888"
                )
            )

    def test_rechaza_fecha_sin_timezone_y_supuestos_no_declarados(self):
        with self.assertRaises(DomainValidationError):
            scenario(evaluated_at=datetime(2026, 8, 8))
        with self.assertRaisesRegex(DomainValidationError, "ASSUMPTION"):
            scenario(assumptions=(result(),))


class MarketplaceContractsTests(unittest.TestCase):
    def test_catalogo_es_inmutable_y_serializable(self):
        catalog = MarketplaceCatalogResult(
            "catalog-1",
            "1",
            NOW,
            marketplaces=(marketplace(),),
            business_models=(business_model(),),
            snapshots=(snapshot(),),
            warnings=("Revisar vigencia",),
        )

        self.assertIsInstance(catalog.marketplaces, tuple)
        self.assertEqual(
            catalog.to_dict()["marketplaces"][0]["marketplace_id"], MARKETPLACE_ID
        )

    def test_assessment_es_multidimensional_sin_score(self):
        assessment = BusinessModelAssessment(
            "assessment-1",
            scenario(),
            "compatible_con_condiciones",
            ConfidenceLevel.MEDIUM,
            "1",
            NOW,
            favorable_factors=("Ajuste de tiempo",),
            unfavorable_factors=("Costo variable",),
            missing_information=("Demanda",),
            evidence=(result(),),
        )
        data = assessment.to_dict()

        self.assertNotIn("score", data)
        self.assertEqual(data["compatibility"], "compatible_con_condiciones")
        self.assertEqual(data["missing_information"], ["Demanda"])

    def test_assessment_rechaza_estado_desconocido(self):
        with self.assertRaises(DomainValidationError):
            BusinessModelAssessment(
                "assessment-1", scenario(), "perfecto", ConfidenceLevel.HIGH, "1", NOW
            )

    def test_scenario_result_requiere_resultados(self):
        contract = OpportunityScenarioResult(scenario(), (result(),))
        self.assertEqual(contract.to_dict()["results"][0]["result_id"], "result-1")
        with self.assertRaises(DomainValidationError):
            OpportunityScenarioResult(scenario(), ())


class CoreIndependenceTests(unittest.TestCase):
    def test_core_no_contiene_nombres_de_programas_especificos(self):
        domain_root = Path(__file__).parents[1] / "domain"
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in domain_root.rglob("*.py")
        ).casefold()

        for forbidden in ("fba", "fbm", "wfs", "seller fulfilled"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
