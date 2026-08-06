import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from domain.enums import ConfidenceLevel, DecisionState, EvidenceType, RiskLevel
from domain.exceptions import DomainValidationError
from domain.value_objects import Money, Percentage


class MoneyTests(unittest.TestCase):
    def test_crea_y_normaliza_dinero_valido(self):
        money = Money("12.50", "usd")

        self.assertEqual(money.amount, Decimal("12.50"))
        self.assertEqual(money.currency, "USD")

    def test_igualdad_depende_del_valor(self):
        self.assertEqual(Money(10, "USD"), Money("10.0", "usd"))
        self.assertNotEqual(Money(10, "USD"), Money(10, "EUR"))
        self.assertEqual(Money(10, "USD") + Money(2, "USD"), Money(12, "USD"))
        with self.assertRaises(DomainValidationError):
            Money(10, "USD") + Money(2, "EUR")

    def test_es_inmutable(self):
        money = Money(10)

        with self.assertRaises(FrozenInstanceError):
            money.amount = Decimal("20")

    def test_rechaza_importe_no_finito_o_booleano(self):
        for value in (True, "texto", float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(DomainValidationError):
                    Money(value)

    def test_rechaza_moneda_invalida(self):
        for currency in ("US", "US12", "", None):
            with self.subTest(currency=currency):
                with self.assertRaises(DomainValidationError):
                    Money(10, currency)

    def test_serializa_sin_perder_precision_decimal(self):
        self.assertEqual(
            Money("10.250", "USD").to_dict(),
            {"amount": "10.250", "currency": "USD"},
        )


class PercentageTests(unittest.TestCase):
    def test_permite_porcentaje_finito_incluso_negativo(self):
        self.assertEqual(Percentage("-12.5").value, Decimal("-12.5"))

    def test_igualdad_depende_del_valor(self):
        self.assertEqual(Percentage(25), Percentage("25.0"))

    def test_es_inmutable(self):
        percentage = Percentage(25)

        with self.assertRaises(FrozenInstanceError):
            percentage.value = Decimal("30")

    def test_rechaza_valores_invalidos(self):
        for value in (False, None, "alto", float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(DomainValidationError):
                    Percentage(value)


class DomainEnumTests(unittest.TestCase):
    def test_enums_tienen_igualdad_por_valor_y_son_inmutables(self):
        self.assertEqual(ConfidenceLevel("alto"), ConfidenceLevel.HIGH)
        self.assertEqual(EvidenceType("dato"), EvidenceType.DATA)
        self.assertEqual(DecisionState("investigar"), DecisionState.INVESTIGATE)
        self.assertEqual(RiskLevel("bajo"), RiskLevel.LOW)

    def test_estado_probar_esta_documentado_como_reserva_del_dominio(self):
        self.assertEqual(DecisionState.TEST.value, "probar")

    def test_rechaza_valores_enumerados_desconocidos(self):
        for enum_type in (
            ConfidenceLevel,
            EvidenceType,
            DecisionState,
            RiskLevel,
        ):
            with self.subTest(enum_type=enum_type):
                with self.assertRaises(ValueError):
                    enum_type("desconocido")


if __name__ == "__main__":
    unittest.main()
