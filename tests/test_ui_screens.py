import unittest

from ui.screens import configuration, preview, ready, results, upload, welcome


class ScreenImportTests(unittest.TestCase):
    def test_todas_las_pantallas_exponen_renderizar(self):
        pantallas = (welcome, upload, preview, ready, configuration, results)

        for pantalla in pantallas:
            with self.subTest(pantalla=pantalla.__name__):
                self.assertTrue(callable(pantalla.renderizar))


if __name__ == "__main__":
    unittest.main()
