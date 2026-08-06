import copy
import unittest

from application.analysis_service import analizar
from application.dashboard_service import crear_dashboard
from application.decision_service import ESTADOS_PERMITIDOS, generar_decision
from application.insight_service import generar_insights


CONTRATO_DECISION = {
    "estado",
    "recomendacion_principal",
    "resumen",
    "evidencia_favorable",
    "riesgos",
    "datos_faltantes",
    "proximo_paso",
    "alternativas",
    "condiciones_para_avanzar",
    "nivel_confianza",
    "reglas_aplicadas",
    "limitaciones",
    "pregunta_de_continuacion",
    "contexto_utilizado",
}


def producto(
    nombre,
    score,
    evaluacion="BUEN PRODUCTO",
    roi=120,
    margen=35,
    ganancia=18,
):
    return {
        "nombre": nombre,
        "roi": roi,
        "margen": margen,
        "ganancia": ganancia,
        "evaluacion": evaluacion,
        "opportunity_score": score,
        "opportunity_category": "Muy prometedora",
    }


def dashboard(resultados, total=None):
    respuesta = crear_dashboard(resultados, total)
    if not respuesta["exito"]:
        raise AssertionError(respuesta["errores"])
    return respuesta["datos"]


def insights_vacios():
    return {
        "titular_principal": "Resumen",
        "resumen_ejecutivo": "Resumen",
        "fortalezas_detectadas": [],
        "riesgos_detectados": [],
        "proximos_pasos_recomendados": [],
        "producto_prioritario": None,
        "advertencias": [],
        "reglas_activadas": [],
    }


def decidir(completos, filtrados=None, contexto=None, filtros=None):
    filtrados = completos if filtrados is None else filtrados
    return generar_decision(
        completos,
        filtrados,
        dashboard(filtrados, len(completos)),
        insights_vacios(),
        filtros or {},
        contexto,
    )


class DecisionServiceTests(unittest.TestCase):
    def test_entrada_vacia_invita_a_explorar_y_respeta_contrato(self):
        respuesta = decidir([], [])

        self.assertTrue(respuesta["exito"])
        self.assertEqual(respuesta["datos"]["estado"], "explorar")
        self.assertEqual(set(respuesta["datos"]), CONTRATO_DECISION)

    def test_oportunidad_favorable_sin_datos_comerciales_pide_investigar(self):
        respuesta = decidir([producto("Líder", 82)])
        datos = respuesta["datos"]

        self.assertEqual(datos["estado"], "investigar")
        self.assertIn("demanda", datos["datos_faltantes"])
        self.assertIn("competencia", datos["datos_faltantes"])
        self.assertIn("datos_comerciales_ausentes", datos["reglas_aplicadas"])

    def test_varias_oportunidades_similares_piden_comparar(self):
        respuesta = decidir(
            [producto("A", 82), producto("B", 79), producto("C", 60)]
        )

        self.assertEqual(respuesta["datos"]["estado"], "comparar")
        self.assertIn(
            "oportunidades_similares_comparar",
            respuesta["datos"]["reglas_aplicadas"],
        )

    def test_presupuesto_bajo_mantiene_investigacion_y_condiciona_la_prueba(self):
        respuesta = decidir(
            [producto("Líder", 82)],
            contexto={"presupuesto": 75},
        )
        datos = respuesta["datos"]

        self.assertEqual(datos["estado"], "investigar")
        self.assertEqual(
            datos["proximo_paso"],
            "Diseñar una posible prueba pequeña y controlada después de confirmar "
            "demanda, competencia, proveedor, costos finales y marketplace.",
        )
        self.assertIn(
            "presupuesto_conocido_sin_habilitar_prueba",
            datos["reglas_aplicadas"],
        )
        self.assertIn("presupuesto_bajo", datos["reglas_aplicadas"])

    def test_el_estado_probar_esta_reservado_y_no_se_genera(self):
        escenarios = (
            decidir([], []),
            decidir([producto("Débil", 20, evaluacion="NO RECOMENDADO")]),
            decidir([producto("Líder", 82)]),
            decidir([producto("Líder", 82)], contexto={"presupuesto": 75}),
            decidir([producto("A", 82), producto("B", 79)]),
        )

        self.assertNotIn("probar", ESTADOS_PERMITIDOS)
        for respuesta in escenarios:
            with self.subTest(estado=respuesta["datos"]["estado"]):
                self.assertNotEqual(respuesta["datos"]["estado"], "probar")

    def test_presupuesto_desconocido_se_solicita_en_la_continuacion(self):
        respuesta = decidir([producto("Líder", 82)])

        self.assertIn(
            "presupuesto máximo",
            respuesta["datos"]["pregunta_de_continuacion"],
        )

    def test_principiante_recibe_una_accion_principal_en_lenguaje_sencillo(self):
        respuesta = decidir(
            [producto("Líder", 82)],
            contexto={"experiencia": "principiante"},
        )
        datos = respuesta["datos"]

        self.assertTrue(datos["proximo_paso"].startswith("Primer paso:"))
        self.assertIn("lenguaje_principiante", datos["reglas_aplicadas"])
        self.assertIsInstance(datos["proximo_paso"], str)

    def test_resultados_financieros_debiles_piden_posponer(self):
        respuesta = decidir(
            [
                producto(
                    "Débil",
                    20,
                    evaluacion="NO RECOMENDADO",
                    roi=10,
                    margen=5,
                    ganancia=1,
                )
            ]
        )

        self.assertEqual(respuesta["datos"]["estado"], "posponer")
        self.assertIn(
            "resultados_debiles_posponer",
            respuesta["datos"]["reglas_aplicadas"],
        )

    def test_mismas_entradas_producen_exactamente_la_misma_decision(self):
        productos = [producto("Líder", 82)]
        contexto = {"presupuesto": 100, "objetivo": "validar una idea"}

        primera = decidir(productos, contexto=contexto)
        segunda = decidir(productos, contexto=contexto)

        self.assertEqual(primera, segunda)

    def test_datos_faltantes_reducen_la_confianza(self):
        respuesta = decidir([producto("Líder", 82)])
        datos = respuesta["datos"]

        self.assertEqual(datos["nivel_confianza"], "bajo")
        self.assertIn(
            "confianza_reducida_por_datos_faltantes",
            datos["reglas_aplicadas"],
        )

    def test_no_promete_rentabilidad_ni_ordena_una_compra_definitiva(self):
        respuesta = decidir(
            [producto("Líder", 90)],
            contexto={"presupuesto": 500},
        )
        texto = " ".join(
            [
                respuesta["datos"]["recomendacion_principal"],
                respuesta["datos"]["resumen"],
                respuesta["datos"]["proximo_paso"],
                *respuesta["datos"]["limitaciones"],
            ]
        ).casefold()

        self.assertNotIn("rentabilidad garantizada", texto)
        self.assertNotIn("compra ahora", texto)
        self.assertNotIn("invierte ahora", texto)
        self.assertNotIn("debes comprar", texto)
        self.assertIn("decisión final", texto)

    def test_distingue_datos_estimaciones_y_supuestos(self):
        respuesta = decidir([producto("Líder", 82)])
        evidencia = respuesta["datos"]["evidencia_favorable"]

        self.assertTrue(any(item.startswith("Dato:") for item in evidencia))
        self.assertTrue(
            any(item.startswith("Estimación financiera:") for item in evidencia)
        )
        self.assertTrue(any(item.startswith("Supuesto:") for item in evidencia))

    def test_rechaza_contexto_invalido_con_error_claro(self):
        respuesta = decidir(
            [producto("Líder", 82)],
            contexto={"presupuesto": -1},
        )

        self.assertFalse(respuesta["exito"])
        self.assertEqual(respuesta["errores"][0]["campo"], "presupuesto")


class DecisionFlowIntegrationTests(unittest.TestCase):
    def test_flujo_completo_produce_decision_sin_recalcular_metricas(self):
        analisis = analizar(
            [
                {"nombre": "A", "costo": 8, "precio": 29.99},
                {"nombre": "B", "costo": 18, "precio": 44.99},
            ]
        )
        datos = analisis["datos"]
        resumen = crear_dashboard(datos["resultados"], datos["total_analizado"])
        insights = generar_insights(
            datos["resultados_completos"],
            datos["resultados"],
            resumen["datos"],
            datos["filtros_aplicados"],
        )
        resultados_antes = copy.deepcopy(datos["resultados"])
        decision = generar_decision(
            datos["resultados_completos"],
            datos["resultados"],
            resumen["datos"],
            insights["datos"],
            datos["filtros_aplicados"],
        )

        self.assertTrue(analisis["exito"])
        self.assertTrue(insights["exito"])
        self.assertTrue(decision["exito"])
        self.assertIn(
            decision["datos"]["estado"],
            {"investigar", "comparar", "posponer"},
        )
        self.assertEqual(datos["resultados"], resultados_antes)


if __name__ == "__main__":
    unittest.main()
