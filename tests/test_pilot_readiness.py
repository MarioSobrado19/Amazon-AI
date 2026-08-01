import csv
import unittest
from io import StringIO
from pathlib import Path

from application import (
    PLANTILLA_CLIENTE_CSV,
    analizar,
    crear_dashboard,
    generar_insights,
    generar_reporte_comercial,
    importar_desde_contenido,
)


class PilotMaterialsTests(unittest.TestCase):
    def test_plantilla_cliente_tiene_contrato_minimo_y_ejemplo(self):
        filas = list(
            csv.DictReader(StringIO(PLANTILLA_CLIENTE_CSV.decode("utf-8")))
        )

        self.assertEqual(tuple(filas[0]), ("nombre", "costo", "precio"))
        self.assertTrue(filas[0]["nombre"])

    def test_archivo_piloto_tiene_40_productos_ficticios_y_variados(self):
        ruta = Path(__file__).parents[1] / "data" / "ejemplo_piloto_40_productos.csv"
        filas = list(csv.DictReader(ruta.read_text(encoding="utf-8").splitlines()))

        self.assertEqual(tuple(filas[0]), ("nombre", "costo", "precio"))
        self.assertEqual(len(filas), 40)
        self.assertTrue(
            all(fila["nombre"].startswith("Ejemplo ficticio: ") for fila in filas)
        )
        self.assertEqual(len({fila["nombre"] for fila in filas}), len(filas))


class PilotEndToEndTests(unittest.TestCase):
    def test_flujo_completo_carga_analisis_insights_y_exportacion_comercial(self):
        ruta = Path(__file__).parents[1] / "data" / "ejemplo_piloto_40_productos.csv"
        importacion = importar_desde_contenido(ruta.read_bytes(), ruta.name)
        self.assertTrue(importacion["exito"])

        productos = importacion["datos"]["productos"]
        analisis = analizar(productos, {"roi_minimo": 50})
        self.assertTrue(analisis["exito"])

        datos = analisis["datos"]
        dashboard = crear_dashboard(datos["resultados"], datos["total_analizado"])
        self.assertTrue(dashboard["exito"])

        insights = generar_insights(
            datos["resultados_completos"],
            datos["resultados"],
            dashboard["datos"],
            datos["filtros_aplicados"],
        )
        self.assertTrue(insights["exito"])

        reporte = generar_reporte_comercial(
            datos["resultados"], dashboard["datos"], insights["datos"]
        )
        self.assertTrue(reporte["exito"])
        texto = reporte["datos"]["contenido"].decode("utf-8")
        self.assertIn("RESUMEN EJECUTIVO", texto)
        self.assertIn("PRODUCTOS PRIORIZADOS", texto)
        self.assertIn("USO RESPONSABLE Y LIMITACIONES", texto)
        self.assertIn("demanda", texto)
        self.assertIn("no garantizan ventas ni rentabilidad", texto)

    def test_reporte_comercial_rechaza_resultados_vacios(self):
        resultado = generar_reporte_comercial([], {}, {})

        self.assertFalse(resultado["exito"])
        self.assertEqual(resultado["errores"][0]["codigo"], "reporte_comercial_vacio")


if __name__ == "__main__":
    unittest.main()
