import copy
import json
import unittest
from dataclasses import replace
from decimal import Decimal

from application.business_model_service import comparar_modelos_operativos
from application.dashboard_service import crear_dashboard
from application.decision_service import generar_decision
from application.decision_service import generar_decision_dominio
from application.adapters.decision_domain_adapter import (
    construir_analisis_decision,
    convertir_recomendacion_a_formato_actual,
)
from domain.contracts import BusinessModelContext, DecisionRecommendation
from domain.enums import ConfidenceLevel, RiskLevel
from domain.value_objects import Money
from tests.test_business_model_service import (
    NOW,
    US,
    catalog,
    context,
    delegated_model,
    direct_model,
)


def producto(nombre="Producto de prueba", score=82):
    return {
        "nombre": nombre,
        "costo_producto": 8.0,
        "precio": 29.99,
        "costo_total": 16.5,
        "ganancia": 13.49,
        "margen": 45.0,
        "roi": 168.6,
        "evaluacion": "EXCELENTE PRODUCTO",
        "opportunity_score": score,
        "opportunity_category": "Muy prometedora",
        "opportunity_factors": {"roi": 35.0, "margen": 25.0, "ganancia": 22.0},
    }


def dashboard(items):
    response = crear_dashboard(items, len(items))
    if not response["exito"]:
        raise AssertionError(response["errores"])
    return response["datos"]


def insights():
    return {
        "riesgos_detectados": ["Riesgo financiero observado."],
    }


def decision(comparison=None, user_context=None, items=None):
    items = [producto()] if items is None else items
    return generar_decision(
        items,
        items,
        dashboard(items),
        insights(),
        {},
        user_context,
        comparison,
    )


def complete_context(**overrides):
    values = {
        "budget": Money("500"),
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


def comparison(user_context=None, models=None):
    return comparar_modelos_operativos(
        catalog(models),
        user_context or complete_context(),
        assessed_at=NOW,
    )


class BusinessModelDecisionIntegrationTests(unittest.TestCase):
    def test_sin_comparacion_conserva_exactamente_salida_heredada(self):
        items = [producto()]
        expected = generar_decision(
            items, items, dashboard(items), insights(), {}, {"presupuesto": 250}
        )
        actual = decision(None, {"presupuesto": 250}, items)

        self.assertEqual(actual, expected)

    def test_contexto_incompleto_mantiene_investigacion_y_pide_completarlo(self):
        result = decision(comparison(BusinessModelContext()))["datos"]

        self.assertEqual(result["estado"], "investigar")
        self.assertIn("completar presupuesto", result["proximo_paso"])
        self.assertEqual(result["nivel_confianza"], "bajo")
        self.assertIn(
            "business_model_context_incomplete", result["reglas_aplicadas"]
        )

    def test_modelo_claramente_compatible_se_presenta_solo_para_estudio(self):
        clean_direct = direct_model(restrictions=())
        expensive_delegated = delegated_model(
            restrictions=(),
            comparison_profile={
                **delegated_model().comparison_profile.to_dict(),
                "minimum_budget_amount": "2000",
            },
        )
        result = decision(
            comparison(complete_context(), (clean_direct, expensive_delegated))
        )["datos"]
        text = " ".join(
            (result["proximo_paso"], *result["evidencia_favorable"])
        ).casefold()

        self.assertEqual(result["estado"], "investigar")
        self.assertIn(clean_direct.name.casefold(), text)
        self.assertIn("no constituye una elección final", text)

    def test_modelo_parcial_expone_dimensiones_limitantes(self):
        result = decision(comparison())["datos"]

        self.assertIn(
            "partially_compatible_business_model", result["reglas_aplicadas"]
        )
        self.assertTrue(
            any("dimensión limitante" in item for item in result["riesgos"])
        )

    def test_restriccion_fuerte_permanece_visible_con_motivo(self):
        user = complete_context(declared_restrictions=("sin logística propia",))
        result = decision(comparison(user))["datos"]
        text = " ".join(result["riesgos"]).casefold()

        self.assertIn("strong_business_model_restriction_visible", result["reglas_aplicadas"])
        self.assertIn("sin logística propia", text)
        self.assertIn("restricciones", text)

    def test_dos_alternativas_razonables_no_producen_ganador(self):
        user = complete_context(
            objective=None,
            operational_control_preference=None,
        )
        bm_comparison = comparison(user)
        result = decision(bm_comparison)["datos"]

        self.assertIsNone(bm_comparison.consideration_model)
        self.assertEqual(result["estado"], "comparar")
        self.assertIn("sin declarar un ganador", result["proximo_paso"])
        self.assertGreaterEqual(len(result["alternativas"]), 2)

    def test_todos_incompatibles_no_inventa_alternativa(self):
        user = complete_context(
            budget=Money("10"),
            available_time_hours=Decimal("1"),
            logistics_capacity="ninguna",
            storage_space="ninguno",
        )
        result = decision(comparison(user))["datos"]

        self.assertEqual(result["estado"], "investigar")
        self.assertIn("no conserva un modelo compatible", result["proximo_paso"])
        self.assertIn("all_business_models_incompatible", result["reglas_aplicadas"])
        self.assertFalse(
            any("modelo operativo" in item.casefold() for item in result["alternativas"])
        )

    def test_principiante_recibe_educacion_antes_del_paso_operativo(self):
        user = context(
            experience="principiante",
            storage_space="ninguno",
            logistics_capacity="baja",
            available_time_hours=Decimal("8"),
            operational_control_preference="bajo",
            objective="simplificar",
        )
        result = decision(
            comparison(user), {"experiencia": "principiante"}
        )["datos"]

        self.assertTrue(result["proximo_paso"].startswith("Paso educativo sugerido"))
        self.assertIn(
            "business_model_beginner_education_first", result["reglas_aplicadas"]
        )
        self.assertTrue(any("riesgo" in item.casefold() for item in result["riesgos"]))

    def test_confianza_baja_no_puede_aumentar_confianza_de_decision(self):
        result = decision(comparison(BusinessModelContext()))["datos"]

        self.assertEqual(result["nivel_confianza"], ConfidenceLevel.LOW.value)
        self.assertIn("business_model_low_confidence", result["reglas_aplicadas"])

    def test_comparacion_parcialmente_vacia_y_confianza_desconocida_degrada_seguro(self):
        original = comparison()
        partial = replace(
            original,
            assessments=(),
            compatible_models=(),
            incompatible_models=(),
            consideration_model=None,
            consideration_reason=None,
            alternatives=(),
            missing_data=("confidence_unknown", "business_models"),
            confidence=ConfidenceLevel.LOW,
        )
        result = decision(partial)["datos"]

        self.assertEqual(result["estado"], "investigar")
        self.assertEqual(result["nivel_confianza"], "bajo")
        self.assertIn("business_model_context_incomplete", result["reglas_aplicadas"])
        self.assertIn("modelo operativo: confidence_unknown", result["datos_faltantes"])

    def test_comparacion_con_un_solo_modelo_lo_presenta_como_opcion_no_orden(self):
        single = comparison(
            complete_context(),
            (direct_model(restrictions=()),),
        )
        result = decision(single)["datos"]
        text = " ".join((result["proximo_paso"], *result["evidencia_favorable"])).casefold()

        self.assertEqual(len(single.assessments), 1)
        self.assertIn("opción de consideración", text)
        self.assertNotIn("debes elegir", text)

    def test_contexto_financiero_favorable_no_oculta_modelos_incompatibles(self):
        incompatible = comparison(
            complete_context(
                budget=Money("10"),
                available_time_hours=Decimal("1"),
                logistics_capacity="ninguna",
                storage_space="ninguno",
            )
        )
        result = decision(incompatible)["datos"]

        self.assertEqual(result["estado"], "investigar")
        self.assertTrue(
            any("82.0/100" in item for item in result["evidencia_favorable"])
        )
        self.assertIn("all_business_models_incompatible", result["reglas_aplicadas"])
        self.assertTrue(result["contexto_utilizado"]["business_model_strong_restrictions"])

    def test_dos_modelos_con_distinta_confianza_conservan_la_menor(self):
        low_confidence = delegated_model(confidence=ConfidenceLevel.LOW)
        mixed = comparison(complete_context(), (direct_model(), low_confidence))
        result = decision(mixed)["datos"]

        self.assertEqual(mixed.confidence, ConfidenceLevel.LOW)
        self.assertEqual(result["nivel_confianza"], "bajo")
        evidence = " ".join(result["evidencia_favorable"])
        self.assertIn(f"{low_confidence.name} =", evidence)
        self.assertIn("confianza bajo", evidence)

    def test_temas_educativos_vacios_no_inventan_un_paso_educativo(self):
        original = comparison()
        assessments = tuple(
            replace(item, educational_topics=(), simplified_for_beginner=True)
            for item in original.assessments
        )
        without_topics = replace(
            original,
            assessments=assessments,
            simplified_for_beginner=True,
        )
        result = decision(
            without_topics, {"experiencia": "principiante"}
        )["datos"]

        self.assertEqual(
            result["contexto_utilizado"]["business_model_educational_topics"],
            (),
        )
        self.assertNotIn(
            "business_model_beginner_education_first", result["reglas_aplicadas"]
        )
        self.assertFalse(result["proximo_paso"].startswith("Paso educativo sugerido"))

    def test_misma_entrada_produce_misma_recomendacion(self):
        bm_comparison = comparison()
        first = decision(bm_comparison)
        second = decision(bm_comparison)

        self.assertEqual(first, second)

    def test_salida_traza_comparacion_version_dimensiones_y_datos_faltantes(self):
        bm_comparison = comparison(BusinessModelContext())
        result = decision(bm_comparison)["datos"]

        self.assertEqual(
            result["contexto_utilizado"]["business_model_comparison_id"],
            bm_comparison.comparison_id,
        )
        self.assertEqual(
            result["contexto_utilizado"]["business_model_comparison_version"],
            bm_comparison.version,
        )
        self.assertTrue(
            any(rule.startswith("business_model_dimension:") for rule in result["reglas_aplicadas"])
        )
        self.assertTrue(
            any(item.startswith("modelo operativo:") for item in result["datos_faltantes"])
        )
        self.assertTrue(result["contexto_utilizado"]["business_models_considered"])
        self.assertTrue(
            result["contexto_utilizado"]["business_model_relevant_dimensions"]
        )
        self.assertTrue(
            result["contexto_utilizado"]["business_model_educational_topics"]
        )

    def test_round_trip_recommendation_conserva_trazabilidad_nueva(self):
        items = [producto()]
        analysis = construir_analisis_decision(items)
        bm_comparison = comparison()
        response = generar_decision_dominio(
            analysis,
            analysis,
            dashboard(items),
            insights(),
            {},
            None,
            bm_comparison,
        )

        self.assertTrue(response["exito"])
        self.assertIsInstance(response["datos"], DecisionRecommendation)
        legacy = convertir_recomendacion_a_formato_actual(response["datos"])
        trace = dict(response["datos"].recommendation.context_used)
        self.assertEqual(
            trace["business_model_comparison_version"], bm_comparison.version
        )
        self.assertEqual(
            tuple(legacy["contexto_utilizado"]["business_models_considered"]),
            trace["business_models_considered"],
        )
        self.assertEqual(
            tuple(legacy["contexto_utilizado"]["business_model_educational_topics"]),
            trace["business_model_educational_topics"],
        )

    def test_no_hay_lenguaje_de_orden_promesa_o_superioridad(self):
        payload = decision(comparison())["datos"]
        text = json.dumps(payload, ensure_ascii=False).casefold()

        for forbidden in (
            "debes elegir",
            "elige este modelo",
            "este modelo te hará ganar",
            "esta es la mejor opción",
            "rentabilidad garantizada",
        ):
            self.assertNotIn(forbidden, text)

    def test_integracion_no_crea_score_nuevo(self):
        result = decision(comparison())["datos"]

        business_model_keys = {
            key
            for key in result["contexto_utilizado"]
            if key.startswith("business_model_")
        }
        self.assertNotIn("business_model_score", business_model_keys)
        self.assertFalse(
            any("business_model_score" in rule for rule in result["reglas_aplicadas"])
        )

    def test_decision_engine_no_muta_comparacion_ni_modelos(self):
        bm_comparison = comparison()
        before = copy.deepcopy(bm_comparison.to_dict())

        decision(bm_comparison)

        self.assertEqual(bm_comparison.to_dict(), before)

    def test_comparacion_invalida_devuelve_error_controlado(self):
        result = decision(object())

        self.assertFalse(result["exito"])
        self.assertEqual(result["errores"][0]["campo"], "comparacion_modelos")


if __name__ == "__main__":
    unittest.main()
