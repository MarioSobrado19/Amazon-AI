import json
import tempfile
import unittest
from pathlib import Path

from config import cargar_configuracion


CONFIGURACION_VALIDA = {
    "rutas": {
        "datos": "data/productos.csv",
        "reportes": "reports",
    },
    "costos": {
        "envio_predeterminado": 3.0,
        "tarifa_amazon_porcentaje": 0.15,
        "otros_costos_predeterminados": 1.0,
    },
    "filtros": {},
    "analisis": {},
}


class ConfigTests(unittest.TestCase):
    def _crear_config(self, directorio, contenido):
        ruta = Path(directorio) / "config.json"
        ruta.write_text(json.dumps(contenido), encoding="utf-8")
        return ruta

    def test_carga_configuracion_valida(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = self._crear_config(directorio, CONFIGURACION_VALIDA)

            configuracion = cargar_configuracion(ruta, directorio)

            self.assertEqual(
                configuracion["data_file"],
                (Path(directorio) / "data" / "productos.csv").resolve(),
            )
            self.assertEqual(
                configuracion["reports_dir"],
                (Path(directorio) / "reports").resolve(),
            )
            self.assertEqual(configuracion["envio_predeterminado"], 3.0)
            self.assertEqual(configuracion["tarifa_amazon_porcentaje"], 0.15)

    def test_rechaza_seccion_faltante(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = self._crear_config(directorio, {"rutas": {}})

            with self.assertRaisesRegex(ValueError, "costos"):
                cargar_configuracion(ruta, directorio)

    def test_rechaza_campo_faltante(self):
        configuracion = json.loads(json.dumps(CONFIGURACION_VALIDA))
        del configuracion["costos"]["envio_predeterminado"]

        with tempfile.TemporaryDirectory() as directorio:
            ruta = self._crear_config(directorio, configuracion)

            with self.assertRaisesRegex(ValueError, "costos.envio_predeterminado"):
                cargar_configuracion(ruta, directorio)

    def test_rechaza_numero_invalido(self):
        configuracion = json.loads(json.dumps(CONFIGURACION_VALIDA))
        configuracion["costos"]["envio_predeterminado"] = -1

        with tempfile.TemporaryDirectory() as directorio:
            ruta = self._crear_config(directorio, configuracion)

            with self.assertRaisesRegex(ValueError, "envio_predeterminado"):
                cargar_configuracion(ruta, directorio)

    def test_rechaza_tarifa_fuera_de_rango(self):
        configuracion = json.loads(json.dumps(CONFIGURACION_VALIDA))
        configuracion["costos"]["tarifa_amazon_porcentaje"] = 1.5

        with tempfile.TemporaryDirectory() as directorio:
            ruta = self._crear_config(directorio, configuracion)

            with self.assertRaisesRegex(ValueError, "tarifa_amazon_porcentaje"):
                cargar_configuracion(ruta, directorio)

    def test_rechaza_json_invalido(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "config.json"
            ruta.write_text("{configuración inválida", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "JSON válido"):
                cargar_configuracion(ruta, directorio)

    def test_rechaza_ruta_absoluta(self):
        configuracion = json.loads(json.dumps(CONFIGURACION_VALIDA))
        configuracion["rutas"]["reportes"] = "/tmp/reportes"

        with tempfile.TemporaryDirectory() as directorio:
            ruta = self._crear_config(directorio, configuracion)

            with self.assertRaisesRegex(ValueError, "rutas.reportes"):
                cargar_configuracion(ruta, directorio)

    def test_rechaza_ruta_con_directorio_padre(self):
        configuracion = json.loads(json.dumps(CONFIGURACION_VALIDA))
        configuracion["rutas"]["datos"] = "../privado.csv"

        with tempfile.TemporaryDirectory() as directorio:
            ruta = self._crear_config(directorio, configuracion)

            with self.assertRaisesRegex(ValueError, r"rutas.datos.*\.\."):
                cargar_configuracion(ruta, directorio)


if __name__ == "__main__":
    unittest.main()
