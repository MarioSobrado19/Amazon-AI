import unittest

from filters import filtrar_productos
from scout import analizar_productos


PRODUCTOS = [
    {
        "nombre": "Organizador de cocina",
        "precio": 29.99,
        "ganancia": 13.49,
        "margen": 45.0,
        "roi": 168.6,
    },
    {
        "nombre": "Lámpara LED",
        "precio": 49.99,
        "ganancia": 23.49,
        "margen": 47.0,
        "roi": 156.6,
    },
    {
        "nombre": "Soporte para laptop",
        "precio": 44.99,
        "ganancia": 16.24,
        "margen": 36.1,
        "roi": 90.2,
    },
]


class ProductFilterTests(unittest.TestCase):
    def test_productos_vacios_o_none_devuelven_lista_vacia(self):
        self.assertEqual(filtrar_productos([]), [])
        self.assertEqual(filtrar_productos(None), [])

    def test_sin_criterios_devuelve_todos(self):
        resultados = filtrar_productos(PRODUCTOS)

        self.assertEqual(resultados, PRODUCTOS)
        self.assertIsNot(resultados, PRODUCTOS)

    def test_filtra_cada_criterio_numerico(self):
        self.assertEqual(len(filtrar_productos(PRODUCTOS, roi_minimo=150)), 2)
        self.assertEqual(len(filtrar_productos(PRODUCTOS, margen_minimo=46)), 1)
        self.assertEqual(len(filtrar_productos(PRODUCTOS, ganancia_minima=20)), 1)
        self.assertEqual(len(filtrar_productos(PRODUCTOS, precio_maximo=30)), 1)

    def test_combina_varios_criterios(self):
        resultados = filtrar_productos(
            PRODUCTOS,
            roi_minimo=150,
            margen_minimo=46,
            precio_maximo=50,
        )

        self.assertEqual([producto["nombre"] for producto in resultados], ["Lámpara LED"])

    def test_busqueda_ignora_mayusculas_y_acentos(self):
        resultados = filtrar_productos(PRODUCTOS, texto_nombre="LAMPARA")

        self.assertEqual([producto["nombre"] for producto in resultados], ["Lámpara LED"])

    def test_no_modifica_la_lista_original(self):
        copia_original = [producto.copy() for producto in PRODUCTOS]

        filtrar_productos(PRODUCTOS, roi_minimo=150)

        self.assertEqual(PRODUCTOS, copia_original)

    def test_scout_aplica_filtros_despues_del_analisis(self):
        productos_sin_analizar = [
            {"nombre": "Organizador de cocina", "costo": 8, "precio": 29.99},
            {"nombre": "Soporte para laptop", "costo": 18, "precio": 44.99},
        ]

        resultados = analizar_productos(
            productos_sin_analizar,
            roi_minimo=150,
            margen_minimo=40,
            ganancia_minima=10,
            precio_maximo=30,
            texto_nombre="COCINA",
        )

        self.assertEqual(
            [producto["nombre"] for producto in resultados],
            ["Organizador de cocina"],
        )
        self.assertIn("roi", resultados[0])
        self.assertIn("evaluacion", resultados[0])


if __name__ == "__main__":
    unittest.main()
