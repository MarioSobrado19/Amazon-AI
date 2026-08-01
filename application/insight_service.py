"""Insights deterministas derivados de resultados financieros ya calculados."""

from collections import Counter

from application.errors import ErrorAplicacion, resultado_exitoso, resultado_fallido


MINIMO_MUCHOS_RESULTADOS = 5
MAXIMO_POCOS_RESULTADOS = 2
PORCENTAJE_FILTRO_RESTRICTIVO = 0.20
PORCENTAJE_CONCENTRACION = 0.75
ROI_ALTO = 150.0
ROI_EQUILIBRADO = 100.0
MARGEN_EQUILIBRADO = 30.0
MARGEN_DEBIL = 30.0
GANANCIA_EQUILIBRADA = 10.0
GANANCIA_BAJA = 10.0
GANANCIA_ALTA = 20.0
CLASIFICACIONES_RECOMENDABLES = {"EXCELENTE PRODUCTO", "BUEN PRODUCTO"}


def _filtros_activos(filtros):
    return {
        nombre: valor
        for nombre, valor in filtros.items()
        if valor is not None and (not isinstance(valor, str) or valor.strip())
    }


def _validar_entradas(resultados_completos, resultados_filtrados, dashboard, filtros):
    if not isinstance(resultados_completos, list):
        return "resultados_completos"
    if not isinstance(resultados_filtrados, list):
        return "resultados_filtrados"
    if not isinstance(dashboard, dict):
        return "dashboard"
    if not isinstance(filtros, dict):
        return "filtros"
    if any(not isinstance(producto, dict) for producto in resultados_completos):
        return "resultados_completos"
    if any(not isinstance(producto, dict) for producto in resultados_filtrados):
        return "resultados_filtrados"
    return None


def generar_insights(
    resultados_completos,
    resultados_filtrados,
    dashboard,
    filtros_activos,
):
    """Interpreta resultados existentes mediante reglas explícitas y comprobables."""
    campo_invalido = _validar_entradas(
        resultados_completos,
        resultados_filtrados,
        dashboard,
        filtros_activos,
    )
    if campo_invalido:
        return resultado_fallido(
            ErrorAplicacion(
                codigo="insights_invalidos",
                mensaje=f"No se pueden generar insights: {campo_invalido} es inválido.",
                campo=campo_invalido,
            )
        )

    fortalezas = []
    riesgos = []
    proximos_pasos = []
    reglas_activadas = []
    filtros = _filtros_activos(filtros_activos)
    total_completo = len(resultados_completos)
    total_filtrado = len(resultados_filtrados)
    producto_prioritario = dashboard.get("producto_destacado")

    try:
        recomendables = [
            producto
            for producto in resultados_filtrados
            if producto["evaluacion"] in CLASIFICACIONES_RECOMENDABLES
        ]
        roi_alto_ganancia_baja = [
            producto
            for producto in resultados_filtrados
            if producto["roi"] >= ROI_ALTO
            and producto["ganancia"] < GANANCIA_BAJA
        ]
        ganancia_alta_margen_debil = [
            producto
            for producto in resultados_filtrados
            if producto["ganancia"] >= GANANCIA_ALTA
            and producto["margen"] < MARGEN_DEBIL
        ]
    except (KeyError, TypeError):
        return resultado_fallido(
            ErrorAplicacion(
                codigo="insights_invalidos",
                mensaje="No se pueden generar insights porque los resultados están incompletos.",
                campo="resultados",
            )
        )

    if total_filtrado == 0:
        reglas_activadas.append("sin_resultados")
        riesgos.append("No hay productos visibles con los criterios actuales.")
        proximos_pasos.append("Revisa los filtros o carga una lista con más productos.")
    elif total_filtrado <= MAXIMO_POCOS_RESULTADOS:
        reglas_activadas.append("pocos_resultados")
        riesgos.append(
            f"Solo {total_filtrado} producto(s) cumplen los criterios; la selección es limitada."
        )
        proximos_pasos.append("Compara más productos antes de tomar una decisión.")
    elif total_filtrado >= MINIMO_MUCHOS_RESULTADOS:
        reglas_activadas.append("muchos_resultados")
        fortalezas.append(
            f"Hay {total_filtrado} productos que permiten comparar varias oportunidades."
        )

    if producto_prioritario:
        try:
            equilibrado = (
                producto_prioritario["roi"] >= ROI_EQUILIBRADO
                and producto_prioritario["margen"] >= MARGEN_EQUILIBRADO
                and producto_prioritario["ganancia"] >= GANANCIA_EQUILIBRADA
            )
        except (KeyError, TypeError):
            return resultado_fallido(
                ErrorAplicacion(
                    codigo="insights_invalidos",
                    mensaje="El producto prioritario del dashboard está incompleto.",
                    campo="dashboard.producto_destacado",
                )
            )
        if equilibrado:
            reglas_activadas.append("producto_equilibrado")
            fortalezas.append(
                f"{producto_prioritario['nombre']} combina ROI, margen y ganancia por encima de los umbrales iniciales."
            )
            proximos_pasos.append(
                f"Valida costos y condiciones reales de {producto_prioritario['nombre']} antes de invertir."
            )

    if roi_alto_ganancia_baja:
        reglas_activadas.append("roi_alto_ganancia_baja")
        nombres = ", ".join(producto["nombre"] for producto in roi_alto_ganancia_baja)
        riesgos.append(
            f"ROI alto con ganancia menor a ${GANANCIA_BAJA:.2f}: {nombres}."
        )
        proximos_pasos.append("Evalúa si el volumen necesario compensa la ganancia por unidad.")

    if ganancia_alta_margen_debil:
        reglas_activadas.append("ganancia_alta_margen_debil")
        nombres = ", ".join(
            producto["nombre"] for producto in ganancia_alta_margen_debil
        )
        riesgos.append(
            f"Ganancia alta con margen menor a {MARGEN_DEBIL:.0f}%: {nombres}."
        )
        proximos_pasos.append("Revisa la sensibilidad ante aumentos de costos o descuentos.")

    if resultados_filtrados and not recomendables:
        reglas_activadas.append("sin_productos_recomendables")
        riesgos.append("Ningún producto visible tiene clasificación Excelente o Bueno.")
        proximos_pasos.append("Busca alternativas con mejor clasificación antes de invertir.")
    elif recomendables:
        fortalezas.append(
            f"{len(recomendables)} producto(s) tienen clasificación Excelente o Bueno."
        )

    if filtros and total_completo:
        proporcion = total_filtrado / total_completo
        if total_filtrado == 0 or proporcion <= PORCENTAJE_FILTRO_RESTRICTIVO:
            reglas_activadas.append("filtros_restrictivos")
            riesgos.append("Los filtros activos podrían ser demasiado restrictivos.")
            proximos_pasos.append("Relaja un criterio a la vez y compara cómo cambia el ranking.")

    if total_filtrado >= 2:
        conteo = Counter(
            producto["evaluacion"] for producto in resultados_filtrados
        )
        clasificacion, cantidad = conteo.most_common(1)[0]
        if cantidad / total_filtrado >= PORCENTAJE_CONCENTRACION:
            reglas_activadas.append("clasificacion_concentrada")
            riesgos.append(
                f"El {cantidad / total_filtrado:.0%} de los resultados comparte la clasificación {clasificacion.title()}."
            )

    if total_filtrado == 0 and filtros and total_completo:
        titular = "Los filtros no dejaron productos para comparar"
    elif total_filtrado == 0:
        titular = "No hay resultados disponibles para interpretar"
    elif not recomendables:
        titular = "Los resultados requieren una revisión cuidadosa"
    elif "producto_equilibrado" in reglas_activadas:
        titular = f"{producto_prioritario['nombre']} destaca por su equilibrio"
    else:
        titular = "Hay oportunidades que vale la pena revisar"

    resumen_ejecutivo = (
        f"Se muestran {total_filtrado} de {total_completo} productos analizados. "
        f"{len(recomendables)} tienen clasificación Excelente o Bueno."
    )
    if not proximos_pasos:
        proximos_pasos.append("Confirma los costos ingresados antes de tomar una decisión.")

    advertencias = [
        "Estos insights usan únicamente los datos cargados y las métricas calculadas; no estiman demanda, competencia, ventas ni condiciones de proveedores.",
        "Las conclusiones apoyan la comparación, pero no garantizan rentabilidad futura.",
    ]

    return resultado_exitoso(
        {
            "titular_principal": titular,
            "resumen_ejecutivo": resumen_ejecutivo,
            "fortalezas_detectadas": fortalezas,
            "riesgos_detectados": riesgos,
            "proximos_pasos_recomendados": list(dict.fromkeys(proximos_pasos)),
            "producto_prioritario": (
                dict(producto_prioritario) if producto_prioritario else None
            ),
            "advertencias": advertencias,
            "reglas_activadas": reglas_activadas,
        }
    )
