import tempfile
import unittest
from pathlib import Path
from unittest import mock

from application.analysis_service import analizar
from application.export_service import EXPORTADORES, exportar
from application.import_service import importar_desde_contenido, importar_desde_ruta
from application.summary_service import resumir


CSV_VALIDO = b"nombre,costo,precio\nOrganizador,8,29.99\nSoporte,18,44.99\n"


class ImportServiceTests(unittest.TestCase):
    def test_importa_desde_contenido_con_contrato_uniforme(self):
        resultado = importar_desde_contenido(CSV_VALIDO)

        self.assertTrue(resultado["exito"])
        self.assertEqual(resultado["errores"], [])
        self.assertEqual(resultado["datos"]["total_productos"], 2)
        self.assertEqual(len(resultado["datos"]["vista_previa"]), 2)

    def test_rechaza_extension_incorrecta(self):
        resultado = importar_desde_contenido(CSV_VALIDO, "productos.txt")

        self.assertFalse(resultado["exito"])
        self.assertEqual(
            resultado["errores"][0]["codigo"],
            "archivo_formato_invalido",
        )

    def test_rechaza_contenido_vacio_sin_crear_archivo_temporal(self):
        with mock.patch(
            "application.import_service.tempfile.NamedTemporaryFile"
        ) as crear_temporal:
            resultado = importar_desde_contenido(b"")

        self.assertFalse(resultado["exito"])
        self.assertEqual(resultado["errores"][0]["codigo"], "archivo_vacio")
        crear_temporal.assert_not_called()

    def test_rechaza_nombre_de_archivo_invalido(self):
        resultado = importar_desde_contenido(CSV_VALIDO, None)

        self.assertFalse(resultado["exito"])
        self.assertEqual(
            resultado["errores"][0]["codigo"],
            "archivo_formato_invalido",
        )

    def test_rechaza_codificacion_invalida(self):
        resultado = importar_desde_contenido(b"\xff\xfe\x00", "productos.csv")

        self.assertFalse(resultado["exito"])
        self.assertEqual(resultado["errores"][0]["codigo"], "archivo_invalido")

    def test_conserva_nombre_original_en_error_de_archivo_cargado(self):
        contenido = b"nombre,costo,precio\nProducto,no-es-numero,20\n"

        resultado = importar_desde_contenido(contenido, "mi_lista.csv")

        self.assertFalse(resultado["exito"])
        self.assertIn("mi_lista.csv", resultado["errores"][0]["mensaje"])
        self.assertNotIn("/tmp", resultado["errores"][0]["mensaje"])
        self.assertNotIn("/var", resultado["errores"][0]["mensaje"])

    def test_elimina_archivo_temporal_despues_de_importar(self):
        ruta_observada = None

        def cargar_temporal(ruta):
            nonlocal ruta_observada
            ruta_observada = Path(ruta)
            self.assertTrue(ruta_observada.exists())
            return [{"nombre": "Producto", "costo": 5.0, "precio": 15.0}]

        with mock.patch(
            "application.import_service.cargar_productos",
            side_effect=cargar_temporal,
        ):
            resultado = importar_desde_contenido(CSV_VALIDO)

        self.assertTrue(resultado["exito"])
        self.assertIsNotNone(ruta_observada)
        self.assertFalse(ruta_observada.exists())

    def test_traduce_error_de_csv(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "productos.csv"
            ruta.write_text("nombre,precio\nProducto,15\n", encoding="utf-8")
            resultado = importar_desde_ruta(ruta)

        self.assertFalse(resultado["exito"])
        self.assertEqual(resultado["errores"][0]["codigo"], "archivo_invalido")

    def test_oculta_detalle_de_error_inesperado_de_importacion(self):
        with mock.patch(
            "application.import_service.cargar_productos",
            side_effect=RuntimeError("secreto interno"),
        ):
            resultado = importar_desde_contenido(CSV_VALIDO)

        self.assertFalse(resultado["exito"])
        self.assertEqual(
            resultado["errores"][0]["codigo"],
            "archivo_no_procesable",
        )
        self.assertNotIn("secreto interno", resultado["errores"][0]["mensaje"])


class AnalysisServiceTests(unittest.TestCase):
    def test_analiza_y_aplica_filtros(self):
        importacion = importar_desde_contenido(CSV_VALIDO)
        productos = importacion["datos"]["productos"]

        resultado = analizar(productos, {"roi_minimo": 150})

        self.assertTrue(resultado["exito"])
        self.assertEqual(resultado["datos"]["total_analizado"], 2)
        self.assertEqual(resultado["datos"]["total_mostrado"], 1)
        self.assertEqual(
            resultado["datos"]["resultados"][0]["nombre"],
            "Organizador",
        )

    def test_sin_coincidencias_es_exito_con_advertencia(self):
        importacion = importar_desde_contenido(CSV_VALIDO)

        resultado = analizar(
            importacion["datos"]["productos"],
            {"roi_minimo": 1000},
        )

        self.assertTrue(resultado["exito"])
        self.assertEqual(resultado["datos"]["resultados"], [])
        self.assertTrue(resultado["advertencias"])

    def test_rechaza_filtro_desconocido(self):
        resultado = analizar(
            [{"nombre": "Producto", "costo": 5, "precio": 20}],
            {"inventado": 10},
        )

        self.assertFalse(resultado["exito"])
        self.assertEqual(resultado["errores"][0]["codigo"], "filtros_desconocidos")

    def test_rechaza_filtros_que_no_son_diccionario(self):
        resultado = analizar(
            [{"nombre": "Producto", "costo": 5, "precio": 20}],
            ["roi_minimo"],
        )

        self.assertFalse(resultado["exito"])
        self.assertEqual(resultado["errores"][0]["codigo"], "filtros_invalidos")

    def test_traduce_error_inesperado_del_motor(self):
        with mock.patch(
            "application.analysis_service.analizar_productos",
            side_effect=RuntimeError("fallo interno"),
        ):
            resultado = analizar(
                [{"nombre": "Producto", "costo": 5, "precio": 20}]
            )

        self.assertFalse(resultado["exito"])
        self.assertEqual(resultado["errores"][0]["codigo"], "analisis_fallido")
        self.assertNotIn("fallo interno", resultado["errores"][0]["mensaje"])

    def test_aplica_configuracion_personalizada(self):
        resultado = analizar(
            [{"nombre": "Producto", "costo": 10, "precio": 40}],
            configuracion={
                "envio_predeterminado": 5,
                "tarifa_amazon_porcentaje": 0.10,
                "otros_costos_predeterminados": 2,
                "roi_excelente": 300,
                "roi_bueno": 200,
                "roi_regular": 100,
            },
        )

        self.assertTrue(resultado["exito"])
        producto = resultado["datos"]["resultados"][0]
        self.assertEqual(producto["costo_total"], 21.0)
        self.assertEqual(producto["evaluacion"], "REGULAR")

    def test_rechaza_configuracion_invalida(self):
        resultado = analizar(
            [{"nombre": "Producto", "costo": 10, "precio": 40}],
            configuracion={"tarifa_amazon_porcentaje": 1.5},
        )

        self.assertFalse(resultado["exito"])
        self.assertEqual(
            resultado["errores"][0]["codigo"],
            "configuracion_invalida",
        )

    def test_rechaza_niveles_de_roi_desordenados(self):
        resultado = analizar(
            [{"nombre": "Producto", "costo": 10, "precio": 40}],
            configuracion={"roi_excelente": 90, "roi_bueno": 100},
        )

        self.assertFalse(resultado["exito"])
        self.assertEqual(resultado["errores"][0]["campo"], "niveles_roi")


class SummaryServiceTests(unittest.TestCase):
    def test_resume_resultados_sin_recalcular(self):
        analisis = analizar(
            [
                {"nombre": "A", "costo": 8, "precio": 29.99},
                {"nombre": "B", "costo": 18, "precio": 44.99},
            ]
        )

        resumen = resumir(analisis["datos"]["resultados"], total_analizado=2)

        self.assertTrue(resumen["exito"])
        self.assertEqual(resumen["datos"]["total_analizado"], 2)
        self.assertEqual(resumen["datos"]["producto_mejor_roi"], "A")
        self.assertEqual(resumen["datos"]["cantidad_excelentes"], 1)

    def test_resume_lista_vacia_sin_error(self):
        resumen = resumir([], total_analizado=2)

        self.assertTrue(resumen["exito"])
        self.assertEqual(resumen["datos"]["total_analizado"], 2)
        self.assertEqual(resumen["datos"]["total_mostrado"], 0)
        self.assertIsNone(resumen["datos"]["mejor_roi"])
        self.assertIsNone(resumen["datos"]["mayor_ganancia"])

    def test_rechaza_resultado_incompleto(self):
        resumen = resumir([{"nombre": "Producto"}])

        self.assertFalse(resumen["exito"])
        self.assertEqual(
            resumen["errores"][0]["codigo"],
            "resultados_invalidos",
        )

    def test_rechaza_total_analizado_incoherente(self):
        resultados = [
            {
                "nombre": "Producto",
                "roi": 100,
                "ganancia": 10,
                "evaluacion": "BUEN PRODUCTO",
            }
        ]

        for total_invalido in (-1, 0, "uno", True):
            with self.subTest(total=total_invalido):
                resumen = resumir(resultados, total_invalido)
                self.assertFalse(resumen["exito"])
                self.assertEqual(
                    resumen["errores"][0]["codigo"],
                    "total_analizado_invalido",
                )


class ExportServiceTests(unittest.TestCase):
    def test_exporta_csv_con_contrato_uniforme(self):
        analisis = analizar(
            [{"nombre": "A", "costo": 8, "precio": 29.99}]
        )

        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "resultado.csv"
            ruta.write_bytes(b"posicion,nombre\n1,A\n")
            with mock.patch.dict(EXPORTADORES, {"csv": lambda _: ruta}):
                resultado = exportar(analisis["datos"]["resultados"], "csv")

        self.assertTrue(resultado["exito"])
        self.assertEqual(resultado["datos"]["formato"], "csv")
        self.assertIn(b"posicion,nombre", resultado["datos"]["contenido"])

    def test_rechaza_exportacion_vacia(self):
        resultado = exportar([], "txt")

        self.assertFalse(resultado["exito"])
        self.assertEqual(resultado["errores"][0]["codigo"], "exportacion_vacia")

    def test_traduce_error_inesperado_del_exportador(self):
        with mock.patch.dict(
            EXPORTADORES,
            {"csv": mock.Mock(side_effect=RuntimeError("fallo interno"))},
        ):
            resultado = exportar(
                [{"nombre": "Producto"}],
                "csv",
            )

        self.assertFalse(resultado["exito"])
        self.assertEqual(resultado["errores"][0]["codigo"], "exportacion_fallida")
        self.assertNotIn("fallo interno", resultado["errores"][0]["mensaje"])


class ApplicationFlowIntegrationTests(unittest.TestCase):
    def test_importa_analiza_resume_y_exporta(self):
        importacion = importar_desde_contenido(CSV_VALIDO)
        self.assertTrue(importacion["exito"])

        analisis = analizar(importacion["datos"]["productos"])
        self.assertTrue(analisis["exito"])

        resumen = resumir(
            analisis["datos"]["resultados"],
            analisis["datos"]["total_analizado"],
        )
        self.assertTrue(resumen["exito"])

        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "resultado.txt"
            ruta.write_text("Reporte", encoding="utf-8")
            with mock.patch.dict(EXPORTADORES, {"txt": lambda _: ruta}):
                exportacion = exportar(analisis["datos"]["resultados"], "txt")

        self.assertTrue(exportacion["exito"])
        self.assertEqual(exportacion["datos"]["total_productos"], 2)


if __name__ == "__main__":
    unittest.main()
