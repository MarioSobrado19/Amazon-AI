"""Materiales y entrega comercial para sesiones piloto asistidas."""

from datetime import date

from application.errors import ErrorAplicacion, resultado_exitoso, resultado_fallido


PLANTILLA_CLIENTE_CSV = (
    "nombre,costo,precio\n"
    "Ejemplo: Organizador de cocina,8.00,29.99\n"
    "Ejemplo: Botella térmica,11.25,29.99\n"
    "Ejemplo: Lámpara LED portátil,14.00,34.99\n"
    "Ejemplo: Set de contenedores,18.75,44.99\n"
    "Ejemplo: Soporte ajustable para laptop,16.50,39.99\n"
    "Ejemplo: Almohada de viaje,9.25,22.99\n"
    "Ejemplo: Kit de bandas elásticas,7.80,19.99\n"
    "Ejemplo: Dispensador de jabón,12.40,31.99\n"
).encode("utf-8")


LIMITACIONES_PILOTO = (
    "Oriva usa solamente los datos proporcionados y cálculos financieros estimados. "
    "No valida demanda, competencia, historial de precios, proveedores, velocidad de "
    "venta, restricciones del marketplace ni riesgo de inventario."
)


def generar_reporte_comercial(resultados, resumen, insights):
    """Genera una entrega legible para clientes sin recalcular métricas."""
    if not isinstance(resultados, list) or not resultados:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="reporte_comercial_vacio",
                mensaje="No hay resultados para preparar el reporte comercial.",
                campo="resultados",
            )
        )
    if not isinstance(resumen, dict) or not isinstance(insights, dict):
        return resultado_fallido(
            ErrorAplicacion(
                codigo="reporte_comercial_invalido",
                mensaje="El resumen o los insights del análisis están incompletos.",
                campo="reporte",
            )
        )

    lineas = [
        "ORIVA — REPORTE DE PRIORIZACIÓN FINANCIERA",
        "=" * 52,
        f"Fecha: {date.today().isoformat()}",
        "",
        "RESUMEN EJECUTIVO",
        insights.get("titular_principal", "Resultados del análisis"),
        insights.get("resumen_ejecutivo", ""),
        "",
        f"Productos analizados: {resumen.get('total_analizado', len(resultados))}",
        f"Productos mostrados: {resumen.get('total_mostrado', len(resultados))}",
        f"Mejor ROI estimado: {resumen.get('mejor_roi', '—')}%",
        f"Mayor ganancia estimada: ${resumen.get('mayor_ganancia', '—')}",
        "",
        "PRODUCTOS PRIORIZADOS",
    ]

    for posicion, producto in enumerate(resultados, start=1):
        lineas.extend(
            [
                f"#{posicion} {producto['nombre']}",
                (
                    f"  Ganancia ${producto['ganancia']:.2f} | "
                    f"Margen {producto['margen']:.1f}% | ROI {producto['roi']:.1f}%"
                ),
                (
                    "  Score financiero estimado: "
                    f"{producto.get('opportunity_score', '—')}/100 — "
                    f"{producto.get('opportunity_category', 'Sin categoría')}"
                ),
                f"  Evaluación: {producto['evaluacion']}",
                "",
            ]
        )

    fortalezas = insights.get("fortalezas_detectadas", [])
    riesgos = insights.get("riesgos_detectados", [])
    pasos = insights.get("proximos_pasos_recomendados", [])
    for titulo, elementos in (
        ("FORTALEZAS DETECTADAS", fortalezas),
        ("RIESGOS Y PUNTOS A VALIDAR", riesgos),
        ("PRÓXIMOS PASOS RECOMENDADOS", pasos),
    ):
        lineas.append(titulo)
        lineas.extend(f"- {elemento}" for elemento in elementos)
        if not elementos:
            lineas.append("- Sin observaciones adicionales.")
        lineas.append("")

    lineas.extend(
        [
            "USO RESPONSABLE Y LIMITACIONES",
            LIMITACIONES_PILOTO,
            "Los resultados apoyan la investigación; no garantizan ventas ni rentabilidad.",
            "",
            "Preparado con Oriva — Beta privada asistida",
        ]
    )
    contenido = "\n".join(lineas).encode("utf-8")
    return resultado_exitoso(
        {
            "nombre_archivo": "oriva_reporte_piloto.txt",
            "contenido": contenido,
            "total_productos": len(resultados),
        }
    )
