import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from application.business_model_service import (
    BUSINESS_MODEL_ENGINE_VERSION,
    comparar_modelos_operativos,
)
from application.marketplace_service import crear_catalogo_marketplace
from domain.contracts import (
    BusinessModelAssessment,
    BusinessModelComparisonResult,
    BusinessModelContext,
)
from domain.entities import BusinessModel, Marketplace, MarketplaceConditionSnapshot
from domain.enums import (
    ConfidenceLevel,
    FreshnessStatus,
    OperationalLoad,
    RiskLevel,
    VerificationStatus,
)
from domain.exceptions import DomainValidationError
from domain.value_objects import Money, Region
from tests.fakes.marketplace_adapter import FakeMarketplaceAdapter


NOW = datetime(2026, 8, 9, 15, tzinfo=timezone.utc)
US = Region("US")
CA = Region("CA")
MARKETPLACE_ID = "71000000-0000-4000-8000-000000000001"
DIRECT_ID = "72000000-0000-4000-8000-000000000001"
DELEGATED_ID = "72000000-0000-4000-8000-000000000002"


def marketplace():
    return Marketplace(
        marketplace_id=MARKETPLACE_ID,
        name="Canal comercial genérico",
        region=US,
        currency="USD",
        source="Catálogo ficticio verificable",
        valid_from=NOW,
        version="catalog/1",
        confidence=ConfidenceLevel.HIGH,
    )


def direct_model(**overrides):
    values = {
        "business_model_id": DIRECT_ID,
        "name": "Operación directa ficticia",
        "region": US,
        "marketplace_id": MARKETPLACE_ID,
        "confidence": ConfidenceLevel.HIGH,
        "version": "model/1",
        "seller_responsibilities": ("preparar pedidos", "gestionar inventario"),
        "marketplace_responsibilities": ("mantener el canal",),
        "requirements": ("capacidad logística",),
        "restrictions": ("validar cobertura regional",),
        "advantages": ("mayor control operativo",),
        "disadvantages": ("mayor dedicación semanal",),
        "risks": ("carga logística",),
        "operational_load": OperationalLoad.HIGH,
        "recommended_experience": "intermedio",
        "source": "Fuente ficticia de modelos",
        "valid_from": NOW,
        "represents_external_conditions": True,
        "comparison_profile": {
            "minimum_budget_amount": "50",
            "budget_currency": "USD",
            "minimum_time_hours": "20",
            "complexity_level": "alto",
            "logistics_requirement": "alta",
            "storage_requirement": "alto",
            "control_level": "alto",
            "scalability_level": "medio",
            "risk_level": "medio",
            "recommended_experience": "intermedio",
            "suitable_objectives": ["control", "aprender"],
            "incompatible_user_restrictions": ["sin logística propia"],
            "educational_topics": ["logística propia", "gestión de inventario"],
        },
    }
    values.update(overrides)
    return BusinessModel(**values)


def delegated_model(**overrides):
    values = {
        "business_model_id": DELEGATED_ID,
        "name": "Operación delegada ficticia",
        "region": US,
        "marketplace_id": MARKETPLACE_ID,
        "confidence": ConfidenceLevel.HIGH,
        "version": "model/1",
        "seller_responsibilities": ("abastecer inventario",),
        "marketplace_responsibilities": ("coordinar parte de la operación",),
        "requirements": ("capital inicial",),
        "restrictions": ("validar disponibilidad",),
        "advantages": ("menor carga cotidiana",),
        "disadvantages": ("menor control directo",),
        "risks": ("dependencia operativa",),
        "operational_load": OperationalLoad.LOW,
        "recommended_experience": "principiante",
        "source": "Fuente ficticia de modelos",
        "valid_from": NOW,
        "represents_external_conditions": True,
        "comparison_profile": {
            "minimum_budget_amount": "200",
            "budget_currency": "USD",
            "minimum_time_hours": "5",
            "complexity_level": "medio",
            "logistics_requirement": "baja",
            "storage_requirement": "bajo",
            "control_level": "bajo",
            "scalability_level": "alto",
            "risk_level": "medio",
            "recommended_experience": "principiante",
            "suitable_objectives": ["escalar", "simplificar"],
            "educational_topics": ["operación delegada", "costos del servicio"],
        },
    }
    values.update(overrides)
    return BusinessModel(**values)


def snapshot():
    channel = marketplace()
    return MarketplaceConditionSnapshot(
        snapshot_id="73000000-0000-4000-8000-000000000001",
        marketplace=channel,
        region=US,
        condition_type="condición operativa ficticia",
        values={"estado": "disponible"},
        source="Fuente ficticia de condiciones",
        consulted_at=NOW,
        effective_at=NOW,
        expires_at=NOW + timedelta(days=30),
        freshness=FreshnessStatus.CURRENT,
        confidence=ConfidenceLevel.HIGH,
        verification_status=VerificationStatus.VERIFIED,
        version="snapshot/1",
    )


def catalog(models=None):
    adapter = FakeMarketplaceAdapter(
        marketplace=marketplace(),
        business_models=tuple(models or (direct_model(), delegated_model())),
        snapshots=(snapshot(),),
    )
    return crear_catalogo_marketplace(adapter, US, generated_at=NOW)


def context(**overrides):
    values = {
        "budget": Money("500", "USD"),
        "experience": "avanzado",
        "available_time_hours": Decimal("30"),
        "objective": "control",
        "risk_tolerance": RiskLevel.HIGH,
        "region": US,
        "logistics_capacity": "alta",
        "storage_space": "amplio",
        "operational_control_preference": "alto",
        "business_stage": "validación",
    }
    values.update(overrides)
    return BusinessModelContext(**values)


class BusinessModelServiceTests(unittest.TestCase):
    def test_compara_multiples_modelos_con_contrato_estable(self):
        result = comparar_modelos_operativos(catalog(), context(), assessed_at=NOW)

        self.assertIsInstance(result, BusinessModelComparisonResult)
        self.assertEqual(result.version, BUSINESS_MODEL_ENGINE_VERSION)
        self.assertEqual(len(result.assessments), 2)
        self.assertEqual(result.assessed_at, NOW)
        self.assertEqual(
            {item.business_model.name for item in result.assessments},
            {"Operación directa ficticia", "Operación delegada ficticia"},
        )

    def test_contexto_A_capital_limitado_y_tiempo_alto_considera_directo(self):
        user = context(budget=Money("100"), objective="control")
        result = comparar_modelos_operativos(catalog(), user, assessed_at=NOW)

        self.assertEqual(result.consideration_model.business_model_id, DIRECT_ID)
        delegated = next(
            item for item in result.assessments if item.business_model.business_model_id == DELEGATED_ID
        )
        self.assertEqual(delegated.compatibility, "incompatible")
        self.assertIn("presupuesto", " ".join(delegated.unfavorable_factors).casefold())

    def test_contexto_B_capital_alto_y_tiempo_bajo_considera_delegado(self):
        user = context(
            available_time_hours=Decimal("6"),
            logistics_capacity="baja",
            storage_space="limitado",
            operational_control_preference="bajo",
            objective="simplificar",
        )
        result = comparar_modelos_operativos(catalog(), user, assessed_at=NOW)

        self.assertEqual(result.consideration_model.business_model_id, DELEGATED_ID)
        direct = next(
            item for item in result.assessments if item.business_model.business_model_id == DIRECT_ID
        )
        self.assertEqual(direct.compatibility, "incompatible")

    def test_contexto_C_principiante_sin_almacenamiento_simplifica_sin_ocultar_riesgos(self):
        user = context(
            experience="principiante",
            storage_space="ninguno",
            logistics_capacity="baja",
            available_time_hours=Decimal("8"),
            operational_control_preference="bajo",
            objective="simplificar",
        )
        result = comparar_modelos_operativos(catalog(), user, assessed_at=NOW)

        self.assertTrue(result.simplified_for_beginner)
        self.assertTrue(all(item.simplified_for_beginner for item in result.assessments))
        self.assertTrue(all(item.risks for item in result.assessments))
        self.assertIn("palabras sencillas", result.continuation_question)

    def test_contexto_D_experto_que_quiere_control_prefiere_coincidencia_explicita(self):
        result = comparar_modelos_operativos(catalog(), context(), assessed_at=NOW)

        self.assertEqual(result.consideration_model.business_model_id, DIRECT_ID)
        self.assertIn("control alto", result.consideration_reason)

    def test_contexto_E_incompleto_reduce_confianza_y_no_inventa_preferencia(self):
        result = comparar_modelos_operativos(
            catalog(), BusinessModelContext(), assessed_at=NOW
        )

        self.assertEqual(result.confidence, ConfidenceLevel.LOW)
        self.assertIsNone(result.consideration_model)
        self.assertTrue(result.missing_data)
        self.assertTrue(
            all(item.compatibility == "indeterminado" for item in result.assessments)
        )

    def test_presupuesto_por_si_solo_no_domina_la_comparacion(self):
        result = comparar_modelos_operativos(
            catalog(), BusinessModelContext(budget=Money("10000")), assessed_at=NOW
        )

        self.assertIsNone(result.consideration_model)
        self.assertEqual(result.confidence, ConfidenceLevel.LOW)
        self.assertTrue(
            all(item.compatibility == "indeterminado" for item in result.assessments)
        )

    def test_contexto_F_contradictorio_no_oculta_restricciones_fuertes(self):
        user = context(
            budget=Money("1000"),
            available_time_hours=Decimal("1"),
            logistics_capacity="ninguna",
            storage_space="ninguno",
            operational_control_preference="alto",
        )
        result = comparar_modelos_operativos(catalog(), user, assessed_at=NOW)

        self.assertEqual(len(result.incompatible_models), 2)
        self.assertIsNone(result.consideration_model)
        self.assertTrue(
            all(
                any(item.evaluation == "incompatible" for item in assessment.dimensions)
                for assessment in result.assessments
            )
        )

    def test_contexto_G_region_incompatible_descarta_ambos_modelos(self):
        result = comparar_modelos_operativos(
            catalog(), context(region=CA), assessed_at=NOW
        )

        self.assertEqual(len(result.incompatible_models), 2)
        self.assertIsNone(result.consideration_model)
        self.assertTrue(
            all(
                any(
                    dimension.dimension == "compatibilidad_regional"
                    and dimension.evaluation == "incompatible"
                    for dimension in item.dimensions
                )
                for item in result.assessments
            )
        )

    def test_contexto_H_ningun_modelo_compatible_no_fuerza_recomendacion(self):
        user = context(
            budget=Money("10"),
            available_time_hours=Decimal("1"),
            logistics_capacity="ninguna",
            storage_space="ninguno",
        )
        result = comparar_modelos_operativos(catalog(), user, assessed_at=NOW)

        self.assertEqual(len(result.incompatible_models), 2)
        self.assertIsNone(result.consideration_model)
        self.assertEqual(result.alternatives, ())

    def test_contexto_I_empate_explicito_conserva_alternativas_sin_ganador(self):
        user = context(
            objective=None,
            operational_control_preference=None,
            available_time_hours=Decimal("30"),
            logistics_capacity="alta",
            storage_space="amplio",
        )
        result = comparar_modelos_operativos(catalog(), user, assessed_at=NOW)

        self.assertIsNone(result.consideration_model)
        self.assertEqual(len(result.alternatives), 2)
        self.assertIn("varias alternativas", result.consideration_reason)

    def test_contexto_J_restriccion_declarada_elimina_modelo_sin_inferencia_textual(self):
        user = context(
            declared_restrictions=("sin logística propia",),
            operational_control_preference=None,
            objective=None,
        )
        result = comparar_modelos_operativos(catalog(), user, assessed_at=NOW)

        direct = next(
            item
            for item in result.assessments
            if item.business_model.business_model_id == DIRECT_ID
        )
        self.assertEqual(direct.compatibility, "incompatible")
        restriction = next(
            item for item in direct.dimensions if item.dimension == "restricciones"
        )
        self.assertEqual(restriction.evaluation, "incompatible")
        self.assertIn("sin logística propia", restriction.explanation)
        self.assertEqual(result.consideration_model.business_model_id, DELEGATED_ID)

    def test_compatibilidad_parcial_identifica_dimensiones_limitantes(self):
        result = comparar_modelos_operativos(catalog(), context(), assessed_at=NOW)

        partial = tuple(
            item
            for item in result.assessments
            if item.compatibility == "compatible_con_condiciones"
        )
        self.assertTrue(partial)
        for assessment in partial:
            limiting = tuple(
                item
                for item in assessment.dimensions
                if item.evaluation in {"desfavorable", "desconocida"}
            )
            self.assertTrue(limiting)
            self.assertTrue(all(item.explanation for item in limiting))

    def test_cada_dimension_explica_evidencia_faltantes_y_confianza(self):
        result = comparar_modelos_operativos(catalog(), context(), assessed_at=NOW)
        assessment = result.assessments[0]

        self.assertEqual(
            {item.dimension for item in assessment.dimensions},
            {
                "capital_requerido",
                "carga_operativa",
                "tiempo_requerido",
                "complejidad",
                "logistica",
                "almacenamiento",
                "escalabilidad",
                "control_del_usuario",
                "experiencia_recomendada",
                "riesgos",
                "restricciones",
                "compatibilidad_regional",
            },
        )
        self.assertTrue(all(item.explanation for item in assessment.dimensions))
        self.assertTrue(all(item.evidence for item in assessment.dimensions))
        self.assertTrue(
            all(isinstance(item.confidence, ConfidenceLevel) for item in assessment.dimensions)
        )

    def test_salida_preserva_responsabilidades_requisitos_riesgos_y_educacion(self):
        assessment = comparar_modelos_operativos(
            catalog(), context(), assessed_at=NOW
        ).assessments[0]

        self.assertEqual(assessment.risks, direct_model().risks)
        self.assertEqual(assessment.requirements, direct_model().requirements)
        self.assertEqual(
            assessment.seller_responsibilities, direct_model().seller_responsibilities
        )
        self.assertIn("logística propia", assessment.educational_topics)

    def test_no_existe_score_unico_en_el_contrato_serializado(self):
        payload = comparar_modelos_operativos(catalog(), context(), assessed_at=NOW).to_dict()

        def keys(value):
            if isinstance(value, dict):
                for key, nested in value.items():
                    yield key.casefold()
                    yield from keys(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from keys(nested)

        self.assertNotIn("score", set(keys(payload)))

    def test_salida_es_serializable_e_inmutable(self):
        result = comparar_modelos_operativos(catalog(), context(), assessed_at=NOW)

        json.dumps(result.to_dict(), ensure_ascii=False)
        with self.assertRaises(FrozenInstanceError):
            result.confidence = ConfidenceLevel.LOW
        with self.assertRaises(AttributeError):
            result.assessments.append(result.assessments[0])

    def test_motor_no_muta_catalogo_modelos_ni_contexto(self):
        source_catalog = catalog()
        user_context = context()
        catalog_before = source_catalog.to_dict()
        models_before = tuple(item.to_dict() for item in source_catalog.business_models)
        context_before = user_context.to_dict()

        comparar_modelos_operativos(source_catalog, user_context, assessed_at=NOW)

        self.assertEqual(source_catalog.to_dict(), catalog_before)
        self.assertEqual(
            tuple(item.to_dict() for item in source_catalog.business_models),
            models_before,
        )
        self.assertEqual(user_context.to_dict(), context_before)

    def test_no_promete_resultados_ni_ordena_elegir_un_modelo(self):
        text = json.dumps(
            comparar_modelos_operativos(catalog(), context(), assessed_at=NOW).to_dict(),
            ensure_ascii=False,
        ).casefold()

        for forbidden in (
            "debes elegir",
            "elige este modelo",
            "te hará ganar",
            "rentabilidad garantizada",
            "mejor opción garantizada",
        ):
            self.assertNotIn(forbidden, text)

    def test_contexto_y_entrada_invalidos_se_rechazan(self):
        with self.assertRaises(DomainValidationError):
            BusinessModelContext(experience="experto absoluto")
        with self.assertRaises(DomainValidationError):
            comparar_modelos_operativos({}, context(), assessed_at=NOW)
        with self.assertRaises(DomainValidationError):
            comparar_modelos_operativos(catalog(), context(), assessed_at=NOW.replace(tzinfo=None))

    def test_business_model_assessment_anterior_sigue_siendo_compatible(self):
        current = comparar_modelos_operativos(catalog(), context(), assessed_at=NOW).assessments[0]
        rebuilt = BusinessModelAssessment(
            assessment_id=current.assessment_id,
            scenario=None,
            compatibility=current.compatibility,
            confidence=current.confidence,
            version=current.version,
            assessed_at=current.assessed_at,
            business_model=current.business_model,
        )

        self.assertEqual(rebuilt.business_model, current.business_model)
        self.assertEqual(rebuilt.dimensions, ())

    def test_servicio_y_contratos_no_contienen_integraciones_ni_formulas_prohibidas(self):
        root = Path(__file__).resolve().parents[1]
        files = (
            root / "application" / "business_model_service.py",
            root / "domain" / "contracts" / "business_model_context.py",
            root / "domain" / "contracts" / "business_model_comparison_result.py",
        )
        source = "\n".join(path.read_text(encoding="utf-8") for path in files).casefold()
        for forbidden in ("amazon", "fba", "fbm", "wfs", "sp-api"):
            self.assertNotIn(forbidden, source)
        for forbidden_formula in ("calcular_roi", "calcular_margen", "opportunity_score"):
            self.assertNotIn(forbidden_formula, source)


if __name__ == "__main__":
    unittest.main()
