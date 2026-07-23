import unittest

from calculator import calcular_rentabilidad
from scout import analizar_productos, clasificar_producto


class CalculatorTests(unittest.TestCase):
    def test_calcula_producto_conocido(self):
        resultado = calcular_rentabilidad("Organizador", 8, 29.99)

        self.assertEqual(resultado["costo_total"], 16.5)
        self.assertEqual(resultado["ganancia"], 13.49)
        self.assertEqual(resultado["margen"], 45.0)
        self.assertEqual(resultado["roi"], 168.6)

    def test_rechaza_costo_invalido(self):
        with self.assertRaises(ValueError):
            calcular_rentabilidad("Producto", 0, 20)

    def test_clasificaciones(self):
        self.assertEqual(clasificar_producto(150), "EXCELENTE PRODUCTO")
        self.assertEqual(clasificar_producto(100), "BUEN PRODUCTO")
        self.assertEqual(clasificar_producto(50), "REGULAR")
        self.assertEqual(clasificar_producto(49.9), "NO RECOMENDADO")

    def test_clasificaciones_con_niveles_personalizados(self):
        niveles = {
            "roi_excelente": 200,
            "roi_bueno": 120,
            "roi_regular": 80,
        }

        self.assertEqual(
            clasificar_producto(120, **niveles),
            "BUEN PRODUCTO",
        )
        self.assertEqual(
            clasificar_producto(79.9, **niveles),
            "NO RECOMENDADO",
        )

    def test_ordena_por_roi(self):
        productos = [
            {"nombre": "B", "costo": 18, "precio": 44.99},
            {"nombre": "A", "costo": 8, "precio": 29.99},
        ]

        resultados = analizar_productos(productos)

        self.assertEqual([producto["nombre"] for producto in resultados], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
