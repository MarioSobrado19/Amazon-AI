import unittest

from ui.screens import (
    configuration,
    controlled_opportunity,
    preview,
    ready,
    results,
    upload,
    welcome,
)
from ui.components.opportunity_dossier import mostrar_expediente


class ScreenImportTests(unittest.TestCase):
    def test_todas_las_pantallas_exponen_renderizar(self):
        pantallas = (
            welcome,
            upload,
            preview,
            ready,
            configuration,
            results,
            controlled_opportunity,
        )

        for pantalla in pantallas:
            with self.subTest(pantalla=pantalla.__name__):
                self.assertTrue(callable(pantalla.renderizar))

        self.assertTrue(callable(mostrar_expediente))


if __name__ == "__main__":
    unittest.main()
