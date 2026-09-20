import unittest

from application.controlled_opportunity_service import (
    analizar_oportunidad_controlada,
    estado_conexion_ebay,
)
from infrastructure.oauth_client import ApiError


class FakeSource:
    environment = "production"

    def load(self):
        return [{
            "nombre": "Producto exacto",
            "precio": 25.0,
            "currency": "USD",
            "condition": "New",
            "ebay_item_id": "v1|1|0",
            "source": "ebay_browse",
        }]

    def get_item(self, item_id):
        return {
            "title": "Producto exacto",
            "condition": "New",
            "localizedAspects": [
                {"name": "UPC", "value": "629721670295"},
                {"name": "Brand", "value": "Marca"},
            ],
            "price": {"currency": "USD"},
        }


class FailingSource:
    environment = "production"

    def __init__(self, error):
        self.error = error

    def load(self):
        raise self.error


class ControlledOpportunityServiceTests(unittest.TestCase):
    def test_estado_conexion_no_expone_secretos(self):
        status = estado_conexion_ebay({
            "EBAY_CLIENT_ID": "client-value",
            "EBAY_CLIENT_SECRET": "secret-value",
            "EBAY_ENVIRONMENT": "production",
            "EBAY_BUY_PRODUCTION_APPROVED": "true",
        })

        self.assertTrue(status["ready"])
        self.assertNotIn("client-value", repr(status))
        self.assertNotIn("secret-value", repr(status))

    def test_no_habilita_sandbox_ni_production_sin_aprobacion(self):
        sandbox = estado_conexion_ebay({
            "EBAY_CLIENT_ID": "id", "EBAY_CLIENT_SECRET": "secret"
        })
        pending = estado_conexion_ebay({
            "EBAY_CLIENT_ID": "id",
            "EBAY_CLIENT_SECRET": "secret",
            "EBAY_ENVIRONMENT": "production",
        })

        self.assertFalse(sandbox["ready"])
        self.assertFalse(pending["ready"])

    def test_valida_gtin_y_costo_antes_de_consultar(self):
        invalid_gtin = analizar_oportunidad_controlada(
            gtin="abc", costo_manual=8, tarifa_porcentaje=13.6, fuente=FakeSource()
        )
        invalid_cost = analizar_oportunidad_controlada(
            gtin="629721670295",
            costo_manual=0,
            tarifa_porcentaje=13.6,
            fuente=FakeSource(),
        )

        self.assertFalse(invalid_gtin["exito"])
        self.assertEqual(invalid_gtin["errores"][0]["codigo"], "gtin_invalido")
        self.assertFalse(invalid_cost["exito"])
        self.assertIn("mayor que 0", invalid_cost["errores"][0]["mensaje"])

    def test_ejecuta_pipeline_y_mantiene_advertencia_comercial(self):
        result = analizar_oportunidad_controlada(
            gtin="629721670295",
            costo_manual=8,
            tarifa_porcentaje=13.6,
            tarifa_fija=.40,
            envio=5,
            empaque=.50,
            fuente=FakeSource(),
        )

        self.assertTrue(result["exito"])
        self.assertEqual(result["datos"]["commercial_status"], "commercially_unverified")
        self.assertFalse(result["datos"]["states"]["research_ready"])
        self.assertTrue(any("no demuestran ventas" in item for item in result["advertencias"]))

    def test_convierte_errores_api_sin_filtrar_detalles_sensibles(self):
        result = analizar_oportunidad_controlada(
            gtin="629721670295",
            costo_manual=8,
            tarifa_porcentaje=13.6,
            fuente=FailingSource(
                ApiError("authentication_failed", "secret-token-raw")
            ),
        )

        self.assertFalse(result["exito"])
        self.assertNotIn("secret-token-raw", repr(result))
        self.assertIn("autenticación", result["errores"][0]["mensaje"])

    def test_rechaza_porcentajes_fuera_de_rango(self):
        result = analizar_oportunidad_controlada(
            gtin="629721670295",
            costo_manual=8,
            tarifa_porcentaje=101,
            fuente=FakeSource(),
        )

        self.assertFalse(result["exito"])
        self.assertIn("100", result["errores"][0]["mensaje"])

    def test_rechaza_nan_e_infinito(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                result = analizar_oportunidad_controlada(
                    gtin="629721670295",
                    costo_manual=value,
                    tarifa_porcentaje=13.6,
                    fuente=FakeSource(),
                )
                self.assertFalse(result["exito"])
                self.assertIn("finito", result["errores"][0]["mensaje"])

    def test_error_inesperado_no_filtra_detalles_internos(self):
        result = analizar_oportunidad_controlada(
            gtin="629721670295",
            costo_manual=8,
            tarifa_porcentaje=13.6,
            fuente=FailingSource(RuntimeError("Authorization: Bearer private-value")),
        )

        self.assertFalse(result["exito"])
        self.assertEqual(result["errores"][0]["codigo"], "error_interno")
        self.assertNotIn("private-value", repr(result))


if __name__ == "__main__":
    unittest.main()
