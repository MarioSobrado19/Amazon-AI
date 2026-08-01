import unittest

from application.dashboard_service import crear_dashboard


class DashboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.resultados = [
            {
                "nombre": "Mayor ganancia",
                "precio": 80.0,
                "costo_total": 40.0,
                "ganancia": 40.0,
                "margen": 50.0,
                "roi": 100.0,
                "evaluacion": "BUEN PRODUCTO",
            },
            {
                "nombre": "Mejor ROI",
                "precio": 30.0,
                "costo_total": 10.0,
                "ganancia": 20.0,
                "margen": 66.7,
                "roi": 200.0,
                "evaluacion": "EXCELENTE PRODUCTO",
            },
            {
                "nombre": "Regular",
                "precio": 20.0,
                "costo_total": 15.0,
                "ganancia": 5.0,
                "margen": 25.0,
                "roi": 33.3,
                "evaluacion": "REGULAR",
            },
            {
                "nombre": "Descartado",
                "precio": 10.0,
                "costo_total": 12.0,
                "ganancia": -2.0,
                "margen": -20.0,
                "roi": -16.7,
                "evaluacion": "NO RECOMENDADO",
            },
        ]

    def test_genera_todos_los_indicadores_y_el_producto_destacado(self):
        respuesta = crear_dashboard(self.resultados, total_analizado=7)

        self.assertTrue(respuesta["exito"])
        datos = respuesta["datos"]
        self.assertEqual(datos["total_analizado"], 7)
        self.assertEqual(datos["total_mostrado"], 4)
        self.assertEqual(datos["mejor_roi"], 200.0)
        self.assertEqual(datos["mayor_ganancia"], 40.0)
        self.assertEqual(datos["cantidad_excelentes"], 1)
        self.assertEqual(datos["cantidad_buenos"], 1)
        self.assertEqual(datos["cantidad_regulares"], 1)
        self.assertEqual(datos["cantidad_no_recomendados"], 1)
        self.assertEqual(datos["producto_destacado"]["nombre"], "Mejor ROI")

    def test_selecciona_el_mejor_roi_sin_depending_del_orden(self):
        respuesta = crear_dashboard(self.resultados)

        self.assertEqual(
            respuesta["datos"]["producto_destacado"]["nombre"], "Mejor ROI"
        )

    def test_acepta_resultados_vacios(self):
        respuesta = crear_dashboard([], total_analizado=3)

        self.assertTrue(respuesta["exito"])
        self.assertEqual(respuesta["datos"]["total_mostrado"], 0)
        self.assertIsNone(respuesta["datos"]["mejor_roi"])
        self.assertIsNone(respuesta["datos"]["producto_destacado"])

    def test_rechaza_un_producto_incompleto_para_el_destacado(self):
        respuesta = crear_dashboard(
            [
                {
                    "nombre": "Incompleto",
                    "roi": 100.0,
                    "ganancia": 10.0,
                    "evaluacion": "BUEN PRODUCTO",
                }
            ]
        )

        self.assertFalse(respuesta["exito"])
        self.assertEqual(respuesta["errores"][0]["codigo"], "resultados_invalidos")

    def test_no_modifica_los_resultados_originales(self):
        copia = [dict(producto) for producto in self.resultados]

        crear_dashboard(self.resultados)

        self.assertEqual(self.resultados, copia)


if __name__ == "__main__":
    unittest.main()
