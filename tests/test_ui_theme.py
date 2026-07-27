import tomllib
import unittest
from pathlib import Path


class ThemeTests(unittest.TestCase):
    def test_el_color_principal_no_es_un_rojo_de_alerta(self):
        ruta = Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml"

        with open(ruta, "rb") as archivo:
            configuracion = tomllib.load(archivo)

        self.assertEqual(configuracion["theme"]["primaryColor"], "#234E70")


if __name__ == "__main__":
    unittest.main()
