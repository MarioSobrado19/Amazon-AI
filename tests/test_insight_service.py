import unittest

from application.analysis_service import analizar
from application.dashboard_service import crear_dashboard
from application.insight_service import generar_insights


def producto(nombre, roi, ganancia, margen, evaluacion):
    return {
        "nombre": nombre,
        "roi": roi,
        "ganancia": ganancia,
        "margen": margen,
        "evaluacion": evaluacion,
    }


def dashboard_para(resultados, total=None):
    respuesta = crear_dashboard(resultados, total)
    if not respuesta["exito"]:
        raise AssertionError(respuesta["errores"])
    return respuesta["datos"]


class InsightServiceTests(unittest.TestCase):
    def test_resultados_normales_generan_estructura_estable(self):
        resultados = [
            producto("Líder", 180, 25, 45, "EXCELENTE PRODUCTO"),
            producto("Alternativa", 110, 15, 35, "BUEN PRODUCTO"),
            producto("Regular", 70, 8, 25, "REGULAR"),
        ]

        respuesta = generar_insights(
            resultados, resultados, dashboard_para(resultados), {}
        )

        self.assertTrue(respuesta["exito"])
        datos = respuesta["datos"]
        self.assertEqual(
            set(datos),
            {
                "titular_principal",
                "resumen_ejecutivo",
                "fortalezas_detectadas",
                "riesgos_detectados",
                "proximos_pasos_recomendados",
                "producto_prioritario",
                "advertencias",
                "reglas_activadas",
            },
        )
        self.assertIn("producto_equilibrado", datos["reglas_activadas"])
        self.assertEqual(datos["producto_prioritario"]["nombre"], "Líder")

    def test_lista_vacia_genera_insight_sin_producto_prioritario(self):
        respuesta = generar_insights([], [], dashboard_para([]), {})

        self.assertTrue(respuesta["exito"])
        self.assertIsNone(respuesta["datos"]["producto_prioritario"])
        self.assertIn("sin_resultados", respuesta["datos"]["reglas_activadas"])

    def test_detecta_ausencia_de_productos_recomendables(self):
        resultados = [
            producto("Regular A", 60, 8, 25, "REGULAR"),
            producto("Regular B", 55, 7, 24, "REGULAR"),
        ]

        respuesta = generar_insights(
            resultados, resultados, dashboard_para(resultados), {}
        )

        self.assertIn(
            "sin_productos_recomendables", respuesta["datos"]["reglas_activadas"]
        )

    def test_detecta_pocos_productos_que_cumplen_criterios(self):
        resultados = [
            producto("Único", 120, 15, 35, "BUEN PRODUCTO")
        ]

        respuesta = generar_insights(
            resultados, resultados, dashboard_para(resultados), {}
        )

        self.assertIn("pocos_resultados", respuesta["datos"]["reglas_activadas"])

    def test_detecta_muchos_resultados_y_clasificacion_concentrada(self):
        resultados = [
            producto(f"Producto {indice}", 110 + indice, 15, 35, "BUEN PRODUCTO")
            for indice in range(5)
        ]

        respuesta = generar_insights(
            resultados, resultados, dashboard_para(resultados), {}
        )

        self.assertIn("muchos_resultados", respuesta["datos"]["reglas_activadas"])
        self.assertIn(
            "clasificacion_concentrada", respuesta["datos"]["reglas_activadas"]
        )

    def test_detecta_filtros_sin_coincidencias(self):
        completos = [producto("Producto", 100, 12, 35, "BUEN PRODUCTO")]

        respuesta = generar_insights(
            completos,
            [],
            dashboard_para([], total=1),
            {"roi_minimo": 500},
        )

        self.assertIn("filtros_restrictivos", respuesta["datos"]["reglas_activadas"])
        self.assertIn("filtros", respuesta["datos"]["titular_principal"].lower())

    def test_detecta_roi_alto_con_ganancia_baja(self):
        resultados = [
            producto("ROI engañoso", 220, 5, 45, "EXCELENTE PRODUCTO")
        ]

        respuesta = generar_insights(
            resultados, resultados, dashboard_para(resultados), {}
        )

        self.assertIn(
            "roi_alto_ganancia_baja", respuesta["datos"]["reglas_activadas"]
        )

    def test_detecta_ganancia_alta_con_margen_bajo(self):
        resultados = [
            producto("Margen sensible", 90, 30, 20, "REGULAR")
        ]

        respuesta = generar_insights(
            resultados, resultados, dashboard_para(resultados), {}
        )

        self.assertIn(
            "ganancia_alta_margen_debil", respuesta["datos"]["reglas_activadas"]
        )


class InsightFlowIntegrationTests(unittest.TestCase):
    def test_flujo_analisis_dashboard_e_insights(self):
        analisis = analizar(
            [
                {"nombre": "A", "costo": 8, "precio": 29.99},
                {"nombre": "B", "costo": 18, "precio": 44.99},
            ],
            {"roi_minimo": 100},
        )
        datos = analisis["datos"]
        dashboard = crear_dashboard(datos["resultados"], datos["total_analizado"])

        insights = generar_insights(
            datos["resultados_completos"],
            datos["resultados"],
            dashboard["datos"],
            datos["filtros_aplicados"],
        )

        self.assertTrue(analisis["exito"])
        self.assertTrue(dashboard["exito"])
        self.assertTrue(insights["exito"])
        self.assertEqual(len(datos["resultados_completos"]), 2)


if __name__ == "__main__":
    unittest.main()
