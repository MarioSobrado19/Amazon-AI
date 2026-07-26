import unittest

from ui.view_models import (
    PLANTILLA_CSV,
    mensajes_de_error,
    construir_filtros,
    preparar_filas,
    preparar_estado_filtros,
    preparar_resultados,
)


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

    def test_prepara_ranking_de_resultados(self):
        filas = preparar_resultados(
            [
                {
                    "nombre": "Producto",
                    "precio": 20.0,
                    "costo_total": 10.0,
                    "ganancia": 10.0,
                    "margen": 50.0,
                    "roi": 100.0,
                    "evaluacion": "BUEN PRODUCTO",
                }
            ]
        )

        self.assertEqual(filas[0]["Posición"], 1)
        self.assertEqual(filas[0]["ROI %"], 100.0)

    def test_prepara_filtros_guardados_para_el_formulario(self):
        estado = preparar_estado_filtros(
            {"roi_minimo": 120, "texto_nombre": "cocina"}
        )

        self.assertTrue(estado["activos"]["roi_minimo"])
        self.assertFalse(estado["activos"]["precio_maximo"])
        self.assertEqual(estado["valores"]["roi_minimo"], 120.0)
        self.assertEqual(estado["texto_nombre"], "cocina")

    def test_construye_solo_filtros_activos(self):
        filtros = construir_filtros(
            {
                "activos": {"roi_minimo": True, "precio_maximo": False},
                "valores": {"roi_minimo": 100.0, "precio_maximo": 50.0},
                "texto_nombre": "  luz  ",
            }
        )

        self.assertEqual(
            filtros,
            {"roi_minimo": 100.0, "texto_nombre": "luz"},
        )


if __name__ == "__main__":
    unittest.main()
