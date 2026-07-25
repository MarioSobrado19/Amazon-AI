import unittest

from ui.navigation import BIENVENIDA
from ui.session import (
    confirmar_importacion,
    guardar_importacion,
    inicializar_sesion,
    reiniciar_sesion,
)


class SessionTests(unittest.TestCase):
    def test_inicializa_sesion_sin_sobrescribir_valores(self):
        estado = {"pantalla_actual": "carga"}

        inicializar_sesion(estado)

        self.assertEqual(estado["pantalla_actual"], "carga")
        self.assertEqual(estado["productos"], [])

    def test_guarda_y_confirma_importacion(self):
        estado = {}
        inicializar_sesion(estado)
        datos = {
            "productos": [{"nombre": "Producto", "costo": 5, "precio": 15}],
            "total_productos": 1,
            "vista_previa": [{"nombre": "Producto", "costo": 5, "precio": 15}],
        }

        guardar_importacion(estado, "productos.csv", datos)

        self.assertEqual(estado["nombre_archivo"], "productos.csv")
        self.assertTrue(confirmar_importacion(estado))
        self.assertTrue(estado["importacion_confirmada"])

    def test_no_confirma_sin_productos(self):
        estado = {"productos": [], "importacion_confirmada": False}

        self.assertFalse(confirmar_importacion(estado))

    def test_reinicia_sesion(self):
        estado = {
            "pantalla_actual": "productos_listos",
            "productos": [{"nombre": "Producto"}],
            "clave_ajena": "se conserva",
        }

        reiniciar_sesion(estado)

        self.assertEqual(estado["pantalla_actual"], BIENVENIDA)
        self.assertEqual(estado["productos"], [])
        self.assertEqual(estado["clave_ajena"], "se conserva")


if __name__ == "__main__":
    unittest.main()
