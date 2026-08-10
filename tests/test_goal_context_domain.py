import math
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from domain.contracts import GoalToBusinessRequest
from domain.entities import Objective
from domain.enums import ConfidenceLevel, InformationSource, RiskLevel
from domain.exceptions import DomainValidationError
from domain.value_objects import (
    CapabilityDeclaration,
    ConstraintDeclaration,
    FrozenMapping,
    GoalContextSnapshot,
    Money,
    PreferenceDeclaration,
    Region,
    ResourceAvailability,
)


NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def objective():
    return Objective("goal-1", "Construir una fuente adicional de ingresos")


def snapshot(**overrides):
    values = {
        "objective_id": "goal-1",
        "captured_at": NOW,
        "version": "1.0",
    }
    values.update(overrides)
    return GoalContextSnapshot(**values)


class ObjectiveTests(unittest.TestCase):
    def test_crea_objetivo_y_compara_por_identidad(self):
        first = objective()
        second = Objective("goal-1", "Descripción actualizada")

        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))

    def test_rechaza_objetivo_incompleto(self):
        with self.assertRaises(DomainValidationError):
            Objective("goal-1", " ")


class ResourceAvailabilityTests(unittest.TestCase):
    def test_permite_recurso_parcial_sin_inventar_disponibilidad(self):
        resource = ResourceAvailability("equipo")

        self.assertIsNone(resource.available)
        self.assertIsNone(resource.quantity)

    def test_normaliza_cantidad_finita_y_serializa(self):
        resource = ResourceAvailability(
            "tiempo",
            available=True,
            quantity="15",
            unit="horas_semana",
            confidence=ConfidenceLevel.HIGH,
        )

        self.assertEqual(resource.quantity, Decimal("15"))
        self.assertEqual(resource.to_dict()["source"], "declarada_por_usuario")

    def test_rechaza_bool_nan_infinito_negativo_y_cantidad_sin_unidad(self):
        invalid = (True, math.nan, math.inf, -1)
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(DomainValidationError):
                    ResourceAvailability("capital", quantity=value, unit="USD")
        with self.assertRaises(DomainValidationError):
            ResourceAvailability("tiempo", quantity=1)

    def test_solo_admite_fuente_declarada_en_esta_version(self):
        with self.assertRaises(DomainValidationError):
            ResourceAvailability("equipo", source=InformationSource.INFERRED)


class DeclarationTests(unittest.TestCase):
    def test_capability_requiere_tipo_y_no_infiere_disponibilidad(self):
        capability = CapabilityDeclaration("sourcing")
        self.assertIsNone(capability.available)
        with self.assertRaises(DomainValidationError):
            CapabilityDeclaration("")

    def test_multiples_capabilities_conservan_valores(self):
        capabilities = (
            CapabilityDeclaration("almacenamiento", available=False),
            CapabilityDeclaration("contenido", available=True, level="básico"),
        )
        context = snapshot(capabilities=capabilities)

        self.assertEqual(context.capabilities, capabilities)

    def test_constraint_requiere_tipo_explicacion_y_timezone(self):
        for values in (
            {"constraint_type": "", "explanation": "Límite", "declared_at": NOW},
            {"constraint_type": "tiempo", "explanation": "", "declared_at": NOW},
            {
                "constraint_type": "tiempo",
                "explanation": "Máximo declarado",
                "declared_at": datetime(2026, 8, 10),
            },
        ):
            with self.subTest(values=values):
                with self.assertRaises(DomainValidationError):
                    ConstraintDeclaration(**values)

    def test_preference_no_se_convierte_en_restriccion(self):
        preference = PreferenceDeclaration(
            "carga_operativa", "baja", "Preferencia, no obligación"
        )
        constraint = ConstraintDeclaration(
            "sin_inventario", "No almacenar inventario", NOW, value=True
        )

        self.assertFalse(preference.is_binding)
        self.assertEqual(preference.to_dict()["declaration_kind"], "preference")
        self.assertNotEqual(type(preference), type(constraint))

    def test_preferencia_y_restriccion_del_mismo_tema_coexisten(self):
        preference = PreferenceDeclaration(
            "inventario", "reducido", "Preferencia por poco inventario"
        )
        constraint = ConstraintDeclaration(
            "inventario", "No almacenar inventario en casa", NOW, value=False
        )
        context = snapshot(preferences=(preference,), constraints=(constraint,))

        self.assertEqual(context.preferences[0].preference_type, "inventario")
        self.assertEqual(context.constraints[0].constraint_type, "inventario")
        self.assertFalse(context.preferences[0].is_binding)

    def test_declaraciones_son_inmutables(self):
        preference = PreferenceDeclaration("riesgo", "bajo")
        with self.assertRaises(FrozenInstanceError):
            preference.value = "alto"


class GoalContextSnapshotTests(unittest.TestCase):
    def test_contexto_completo_valido(self):
        context = snapshot(
            available_budget=Money("1500", "USD"),
            available_time_hours_per_week="15",
            experience="principiante",
            risk_tolerance=RiskLevel.LOW,
            region=Region("US", "NY"),
            business_stage="exploración",
            logistics_capacity="limitada",
            storage_space="sin espacio dedicado",
            resources=(ResourceAvailability("equipo", available=True),),
            capabilities=(CapabilityDeclaration("contenido", available=True),),
            constraints=(
                ConstraintDeclaration(
                    "capital_maximo", "No superar el presupuesto", NOW, "1500"
                ),
            ),
            preferences=(PreferenceDeclaration("riesgo", "bajo"),),
        )

        self.assertEqual(context.currency, "USD")
        self.assertEqual(context.available_time_hours_per_week, Decimal("15"))
        self.assertEqual(context.missing_fields(), ())

    def test_contexto_vacio_es_explicito(self):
        context = snapshot()

        self.assertEqual(context.source, InformationSource.USER_DECLARED)
        self.assertIsNone(context.available_budget)
        self.assertIsNone(context.currency)
        self.assertIn("available_budget", context.missing_fields())
        self.assertIn("currency", context.missing_fields())
        self.assertIn("region", context.missing_fields())
        self.assertEqual(context.resources, ())

    def test_serializacion_vacia_conserva_none_y_campos_ausentes(self):
        serialized = snapshot().to_dict()

        for field_name in (
            "available_budget",
            "currency",
            "available_time_hours_per_week",
            "experience",
            "risk_tolerance",
            "region",
            "business_stage",
            "logistics_capacity",
            "storage_space",
        ):
            self.assertIn(field_name, serialized)
            self.assertIsNone(serialized[field_name])
        self.assertEqual(serialized["resources"], [])
        self.assertEqual(serialized["capabilities"], [])
        self.assertEqual(serialized["constraints"], [])
        self.assertEqual(serialized["preferences"], [])

    def test_presupuesto_y_tiempo_cero_son_validos_y_no_ausentes(self):
        context = snapshot(
            available_budget=Money("0", "USD"),
            available_time_hours_per_week=0,
        )

        self.assertEqual(context.available_budget.amount, Decimal("0"))
        self.assertEqual(context.available_time_hours_per_week, Decimal("0"))
        self.assertNotIn("available_budget", context.missing_fields())
        self.assertNotIn("available_time_hours_per_week", context.missing_fields())

    def test_moneda_puede_conocerse_sin_presupuesto(self):
        context = snapshot(currency="usd")

        self.assertEqual(context.currency, "USD")
        self.assertIsNone(context.available_budget)

    def test_moneda_debe_ser_valida_y_coincidir_con_presupuesto(self):
        with self.assertRaises(DomainValidationError):
            snapshot(currency="dólar")
        with self.assertRaises(DomainValidationError):
            snapshot(available_budget=Money("10", "USD"), currency="EUR")

    def test_rechaza_presupuesto_negativo_tiempo_invalido_y_tipos_incorrectos(self):
        invalid_cases = (
            {"available_budget": Money("-1", "USD")},
            {"available_time_hours_per_week": -1},
            {"available_time_hours_per_week": True},
            {"available_time_hours_per_week": math.nan},
            {"risk_tolerance": "bajo"},
            {"region": "US"},
        )
        for overrides in invalid_cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(DomainValidationError):
                    snapshot(**overrides)

    def test_requiere_timezone_y_version(self):
        with self.assertRaises(DomainValidationError):
            snapshot(captured_at=datetime(2026, 8, 10, 12, 0))
        with self.assertRaises(DomainValidationError):
            snapshot(version=" ")
        with self.assertRaises(DomainValidationError):
            snapshot(source=InformationSource.INFERRED)

    def test_preserva_timezone_en_serializacion(self):
        offset = timezone(timedelta(hours=-4))
        context = snapshot(captured_at=datetime(2026, 8, 10, 8, 0, tzinfo=offset))

        self.assertTrue(context.to_dict()["captured_at"].endswith("-04:00"))

    def test_snapshots_del_mismo_objetivo_son_historicos_independientes(self):
        first = snapshot(available_budget=Money("100", "USD"), version="1")
        second = snapshot(
            available_budget=Money("200", "USD"),
            version="2",
            captured_at=NOW + timedelta(days=1),
        )

        self.assertEqual(first.objective_id, second.objective_id)
        self.assertNotEqual(first, second)
        self.assertEqual(first.available_budget.amount, Decimal("100"))

    def test_copia_colecciones_a_tuplas_inmutables(self):
        source = [CapabilityDeclaration("transporte", available=True)]
        context = snapshot(capabilities=source)
        source.clear()

        self.assertEqual(len(context.capabilities), 1)
        with self.assertRaises(FrozenInstanceError):
            context.experience = "avanzado"

    def test_rechaza_colecciones_con_tipos_incorrectos(self):
        with self.assertRaises(DomainValidationError):
            snapshot(preferences=(object(),))

    def test_serializacion_no_expone_colecciones_internas(self):
        context = snapshot(
            capabilities=(CapabilityDeclaration("contenido", available=True),)
        )
        serialized = context.to_dict()
        serialized["capabilities"].append({"capability_type": "inventada"})

        self.assertEqual(len(context.capabilities), 1)


class GoalToBusinessRequestTests(unittest.TestCase):
    def test_crea_solicitud_valida_y_serializable(self):
        request = GoalToBusinessRequest(
            objective(),
            snapshot(),
            "1.0",
            project_id="project-1",
            additional_context={"scope": {"region": "US"}},
        )

        serialized = request.to_dict()
        self.assertEqual(serialized["objective"]["objective_id"], "goal-1")
        self.assertEqual(serialized["context"]["objective_id"], "goal-1")
        self.assertEqual(serialized["additional_context"]["scope"]["region"], "US")

    def test_requiere_objetivo_y_contexto_validos(self):
        with self.assertRaises(DomainValidationError):
            GoalToBusinessRequest(object(), snapshot(), "1")
        with self.assertRaises(DomainValidationError):
            GoalToBusinessRequest(objective(), object(), "1")

    def test_rechaza_contexto_de_otro_objetivo(self):
        with self.assertRaises(DomainValidationError):
            GoalToBusinessRequest(objective(), snapshot(objective_id="goal-2"), "1")

    def test_requiere_version_del_contrato(self):
        with self.assertRaises(DomainValidationError):
            GoalToBusinessRequest(objective(), snapshot(), " ")

    def test_contexto_adicional_queda_congelado(self):
        source = {"questions": ["demanda"]}
        request = GoalToBusinessRequest(
            objective(), snapshot(), "1", additional_context=source
        )
        source["questions"].append("competencia")

        self.assertEqual(
            request.additional_context,
            FrozenMapping.from_mapping({"questions": ["demanda"]}),
        )


if __name__ == "__main__":
    unittest.main()
