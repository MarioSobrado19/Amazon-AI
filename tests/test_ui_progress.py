import unittest

from ui.components.progress import PASOS


class ProgressTests(unittest.TestCase):
    def test_define_el_recorrido_completo_en_orden(self):
        self.assertEqual(PASOS["carga"], (1, "Carga"))
        self.assertEqual(PASOS["vista_previa"], (2, "Revisión"))
        self.assertEqual(PASOS["configuracion"], (3, "Configuración"))
        self.assertEqual(PASOS["resultados"], (4, "Resultados"))


if __name__ == "__main__":
    unittest.main()
