import unittest

from application.analysis_service import analizar
from application.dashboard_service import crear_dashboard
from application.insight_service import generar_insights
from application.opportunity_service import (
    PESO_GANANCIA,
    PESO_MARGEN,
    PESO_ROI,
    categorizar_oportunidad,
    puntuar_oportunidades,
    puntuar_producto,
)
from ui.components.opportunity import DESCRIPCION_SCORE, LIMITACIONES_SCORE
from ui.view_models import preparar_resultados


def producto(roi, margen, ganancia):
    return {
        "nombre": "Producto",
        "roi": roi,
        "margen": margen,
        "ganancia": ganancia,
        "evaluacion": "BUEN PRODUCTO",
    }


class OpportunityServiceTests(unittest.TestCase):
    def test_calcula_aportes_y_puntaje_total(self):
        respuesta = puntuar_producto(producto(100, 25, 15))

        self.assertTrue(respuesta["exito"])
        datos = respuesta["datos"]
        self.assertEqual(datos["opportunity_score"], 50.0)
        self.assertEqual(datos["opportunity_category"], "Analizar con cuidado")
        self.assertEqual(datos["opportunity_factors"]["roi"]["puntos"], 20.0)
        self.assertEqual(datos["opportunity_factors"]["margen"]["puntos"], 15.0)
        self.assertEqual(datos["opportunity_factors"]["ganancia"]["puntos"], 15.0)

    def test_limita_el_puntaje_entre_cero_y_cien(self):
        maximo = puntuar_producto(producto(500, 90, 100))["datos"]
        minimo = puntuar_producto(producto(-50, -10, -5))["datos"]

        self.assertEqual(maximo["opportunity_score"], 100.0)
        self.assertEqual(minimo["opportunity_score"], 0.0)

    def test_asigna_todas_las_categorias(self):
        casos = (
            (100, "Excepcional"),
            (85, "Excepcional"),
            (84.9, "Muy prometedora"),
            (70, "Muy prometedora"),
            (69.9, "Interesante"),
            (55, "Interesante"),
            (54.9, "Analizar con cuidado"),
            (35, "Analizar con cuidado"),
            (34.9, "No prioritaria"),
            (0, "No prioritaria"),
        )

        for puntaje, categoria in casos:
            with self.subTest(puntaje=puntaje):
                self.assertEqual(categorizar_oportunidad(puntaje), categoria)

    def test_conserva_los_pesos_aprobados(self):
        self.assertEqual((PESO_ROI, PESO_MARGEN, PESO_GANANCIA), (40, 30, 30))

    def test_contribuciones_suman_el_score_respetando_el_redondeo(self):
        casos = (
            producto(123.456, 33.333, 12.345),
            producto(500, 90, 100),
            producto(-50, -10, -5),
        )

        for caso in casos:
            with self.subTest(caso=caso):
                datos = puntuar_producto(caso)["datos"]
                suma = sum(
                    factor["puntos"]
                    for factor in datos["opportunity_factors"].values()
                )
                self.assertEqual(datos["opportunity_score"], round(suma, 1))

    def test_valores_extremos_permanecen_dentro_del_rango(self):
        maximo = puntuar_producto(producto(1e308, 1e308, 1e308))["datos"]
        minimo = puntuar_producto(producto(-1e308, -1e308, -1e308))["datos"]

        self.assertEqual(maximo["opportunity_score"], 100.0)
        self.assertEqual(minimo["opportunity_score"], 0.0)

    def test_rechaza_valores_inesperados_no_finitos(self):
        for valor in (float("nan"), float("inf"), float("-inf"), True, None):
            with self.subTest(valor=valor):
                respuesta = puntuar_producto(producto(valor, 25, 15))
                self.assertFalse(respuesta["exito"])
                self.assertEqual(respuesta["errores"][0]["campo"], "roi")

    def test_presentacion_declara_base_y_limitaciones(self):
        descripcion = DESCRIPCION_SCORE.casefold()
        limitaciones = LIMITACIONES_SCORE.casefold()

        for metrica in ("roi", "margen", "ganancia"):
            self.assertIn(metrica, descripcion)
        for limitacion in (
            "demanda",
            "competencia",
            "historial de precios",
            "proveedores",
            "velocidad de venta",
            "riesgo de inventario",
        ):
            self.assertIn(limitacion, limitaciones)

    def test_no_modifica_el_producto_original(self):
        original = producto(100, 25, 15)
        copia = dict(original)

        puntuar_producto(original)

        self.assertEqual(original, copia)

    def test_rechaza_metricas_invalidas(self):
        respuesta = puntuar_producto(producto("alto", 25, 15))

        self.assertFalse(respuesta["exito"])
        self.assertEqual(respuesta["errores"][0]["campo"], "roi")

    def test_puntua_una_lista_sin_cambiar_el_orden(self):
        productos = [producto(50, 20, 5), producto(200, 50, 30)]
        productos[0]["nombre"] = "Primero"
        productos[1]["nombre"] = "Segundo"

        respuesta = puntuar_oportunidades(productos)

        self.assertEqual(
            [item["nombre"] for item in respuesta["datos"]],
            ["Primero", "Segundo"],
        )


class OpportunityFlowIntegrationTests(unittest.TestCase):
    def test_flujo_incluye_score_en_dashboard_insights_y_tabla(self):
        analisis = analizar(
            [{"nombre": "A", "costo": 8, "precio": 29.99}]
        )
        datos = analisis["datos"]
        dashboard = crear_dashboard(datos["resultados"], 1)
        insights = generar_insights(
            datos["resultados_completos"],
            datos["resultados"],
            dashboard["datos"],
            datos["filtros_aplicados"],
        )
        tabla = preparar_resultados(datos["resultados"])

        self.assertTrue(analisis["exito"])
        self.assertIn("opportunity_score", dashboard["datos"]["producto_destacado"])
        self.assertIn(
            "opportunity_score_alto", insights["datos"]["reglas_activadas"]
        )
        self.assertIsInstance(tabla[0]["Score financiero estimado"], float)

    def test_insights_advierte_cuando_el_score_prioritario_es_bajo(self):
        puntuados = puntuar_oportunidades(
            [producto(20, 10, 2)]
        )["datos"]
        dashboard = crear_dashboard(puntuados, 1)

        insights = generar_insights(
            puntuados,
            puntuados,
            dashboard["datos"],
            {},
        )

        self.assertIn(
            "opportunity_score_bajo", insights["datos"]["reglas_activadas"]
        )


if __name__ == "__main__":
    unittest.main()
