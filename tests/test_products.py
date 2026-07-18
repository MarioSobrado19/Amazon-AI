import tempfile
import unittest
from pathlib import Path

from products import cargar_productos


class ProductLoaderTests(unittest.TestCase):
    def test_carga_csv_valido(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "productos.csv"
            ruta.write_text("nombre,costo,precio\nProducto,5,15\n", encoding="utf-8")

            productos = cargar_productos(ruta)

        self.assertEqual(
            productos,
            [{"nombre": "Producto", "costo": 5.0, "precio": 15.0}],
        )

    def test_rechaza_columnas_incompletas(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "productos.csv"
            ruta.write_text("nombre,precio\nProducto,15\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                cargar_productos(ruta)


if __name__ == "__main__":
    unittest.main()
