"""Tarjetas de indicadores del dashboard de resultados."""


def _valor_o_guion(valor, formato):
    return formato.format(valor) if valor is not None else "—"


def mostrar_dashboard(st, resumen):
    indicadores = (
        ("Productos analizados", resumen["total_analizado"]),
        ("Productos mostrados", resumen["total_mostrado"]),
        ("Mejor ROI", _valor_o_guion(resumen["mejor_roi"], "{:.1f}%")),
        (
            "Mayor ganancia",
            _valor_o_guion(resumen["mayor_ganancia"], "${:.2f}"),
        ),
        ("Excelentes", resumen["cantidad_excelentes"]),
        ("Buenos", resumen["cantidad_buenos"]),
        ("Regulares", resumen["cantidad_regulares"]),
        ("No recomendados", resumen["cantidad_no_recomendados"]),
    )

    for inicio in range(0, len(indicadores), 4):
        columnas = st.columns(4)
        for columna, (etiqueta, valor) in zip(
            columnas, indicadores[inicio : inicio + 4]
        ):
            columna.metric(etiqueta, valor)
