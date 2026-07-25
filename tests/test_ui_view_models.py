import unittest

from ui.view_models import PLANTILLA_CSV, mensajes_de_error, preparar_filas


class ViewModelTests(unittest.TestCase):
    def test_plantilla_incluye_varios_productos_de_ejemplo(self):
        lineas = PLANTILLA_CSV.decode("utf-8").strip().splitlines()

        self.assertEqual(lineas[0], "nombre,costo,precio")
        self.assertEqual(len(lineas) - 1, 8)

    def test_prepara_productos_para_tabla(self):
        filas = preparar_filas(
            [{"nombre": "Producto", "costo": 5.0, "precio": 15.0}]
        )

        self.assertEqual(
            filas,
            [{"Nombre": "Producto", "Costo": 5.0, "Precio": 15.0}],
        )

    def test_extrae_mensajes_sin_exponer_otras_propiedades(self):
        resultado = {
            "errores": [
                {
                    "codigo": "archivo_invalido",
                    "mensaje": "Corrige el archivo.",
                    "detalle_interno": "no mostrar",
                }
            ]
        }

        self.assertEqual(mensajes_de_error(resultado), ["Corrige el archivo."])


if __name__ == "__main__":
    unittest.main()
