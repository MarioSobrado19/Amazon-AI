import unittest

from ui.navigation import (
    BIENVENIDA,
    CARGA,
    PRODUCTOS_LISTOS,
    VISTA_PREVIA,
    ir_a,
)


class NavigationTests(unittest.TestCase):
    def test_permite_flujo_valido(self):
        estado = {"pantalla_actual": BIENVENIDA, "productos": []}

        self.assertTrue(ir_a(estado, CARGA))
        estado["productos"] = [{"nombre": "Producto"}]
        self.assertTrue(ir_a(estado, VISTA_PREVIA))
        estado["importacion_confirmada"] = True
        self.assertTrue(ir_a(estado, PRODUCTOS_LISTOS))

    def test_impide_vista_previa_sin_productos(self):
        estado = {"pantalla_actual": CARGA, "productos": []}

        self.assertFalse(ir_a(estado, VISTA_PREVIA))
        self.assertEqual(estado["pantalla_actual"], BIENVENIDA)

    def test_impide_confirmacion_sin_importacion_confirmada(self):
        estado = {
            "pantalla_actual": VISTA_PREVIA,
            "productos": [{"nombre": "Producto"}],
            "importacion_confirmada": False,
        }

        self.assertFalse(ir_a(estado, PRODUCTOS_LISTOS))
        self.assertEqual(estado["pantalla_actual"], BIENVENIDA)

    def test_pantalla_desconocida_regresa_al_inicio(self):
        estado = {"pantalla_actual": CARGA}

        self.assertFalse(ir_a(estado, "pantalla_inventada"))
        self.assertEqual(estado["pantalla_actual"], BIENVENIDA)


if __name__ == "__main__":
    unittest.main()
