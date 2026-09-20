import unittest

from ui.components.controlled_opportunity import filas_escenarios, filas_listings


class ControlledOpportunityViewModelTests(unittest.TestCase):
    def test_filas_listings_distinguen_unknown_conflictos_y_outliers(self):
        rows = filas_listings({
            "listings": [{
                "nombre": "Listing",
                "advertised_price": 20,
                "shipping": None,
                "delivered_price": None,
                "is_price_outlier": True,
                "presentation_validation": {
                    "accepted": False,
                    "unknown": ["quantity"],
                    "conflicts": ["condition"],
                },
            }]
        })

        self.assertEqual(rows[0]["Presentación"], "No comparable")
        self.assertEqual(rows[0]["Envío observado"], "—")
        self.assertEqual(rows[0]["Datos sin confirmar"], "quantity")
        self.assertEqual(rows[0]["Conflictos"], "condition")
        self.assertEqual(rows[0]["Atípico"], "Sí")

    def test_filas_escenarios_dicen_precio_anunciado_y_costo_declarado(self):
        rows = filas_escenarios([{
            "market_listing": {"nombre": "Listing"},
            "economics": {
                "known": {"resale_price": 20, "cost": 8},
                "costo_total": 12,
                "ganancia": 8,
                "margen": 40,
                "roi": 100,
            },
            "oriva": {
                "opportunity_score": 80,
                "opportunity_category": "Muy prometedora",
            },
        }])

        self.assertEqual(rows[0]["Precio anunciado"], "$20.00")
        self.assertEqual(rows[0]["Costo declarado"], "$8.00")
        self.assertEqual(rows[0]["Score financiero"], 80)


if __name__ == "__main__":
    unittest.main()
