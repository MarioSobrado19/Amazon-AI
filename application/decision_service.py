"""Decisiones financieras explicables a partir de resultados ya calculados."""

from application.adapters.decision_domain_adapter import (
    construir_analisis_decision,
    construir_recomendacion_dominio,
    convertir_recomendacion_a_formato_actual,
    convertir_resultados_a_formato_actual,
)
from application.errors import ErrorAplicacion, resultado_exitoso, resultado_fallido
from application.opportunity_service import (
    PUNTAJE_ANALIZAR_CON_CUIDADO,
    PUNTAJE_INTERESANTE,
    PUNTAJE_MUY_PROMETEDORA,
)
from domain.contracts import (
    AnalysisResult,
    BusinessModelComparisonResult,
    DecisionRecommendation,
)
from domain.exceptions import DomainValidationError


ESTADOS_PERMITIDOS = {
    "explorar",
    "investigar",
    "comparar",
    "posponer",
}

# Se reserva para una fase futura con señales comerciales verificadas.
ESTADO_FUTURO_PRUEBA = "probar"

EXPERIENCIAS_PERMITIDAS = {"principiante", "intermedio", "avanzado"}
ETAPAS_PERMITIDAS = {
    "idea",
    "investigacion",
    "validacion",
    "operacion",
    "escalamiento",
}
TOLERANCIAS_PERMITIDAS = {"baja", "media", "alta"}
CLASIFICACIONES_RECOMENDABLES = {"EXCELENTE PRODUCTO", "BUEN PRODUCTO"}
DIFERENCIA_OPORTUNIDADES_SIMILARES = 5.0
PRESUPUESTO_BAJO = 100.0

DATOS_COMERCIALES_AUSENTES = (
    "demanda",
    "competencia",
    "historial de precios",
    "proveedores",
    "velocidad de venta",
    "riesgo de inventario",
)

LIMITACIONES = (
    "La recomendación usa métricas financieras estimadas y el contexto declarado por el usuario.",
    "No evalúa demanda, competencia, historial de precios, proveedores, velocidad de venta ni riesgo de inventario.",
    "El Opportunity Score apoya la comparación, pero no garantiza ventas ni rentabilidad.",
    "La decisión final y cualquier inversión permanecen bajo control del usuario.",
)


def _error(campo, mensaje):
    return resultado_fallido(
        ErrorAplicacion(
            codigo="decision_invalida",
            mensaje=f"No se puede generar la decisión: {mensaje}",
            campo=campo,
        )
    )


def _validar_entradas(
    resultados_completos,
    resultados_filtrados,
    dashboard,
    insights,
    filtros_activos,
):
    colecciones = (
        ("resultados_completos", resultados_completos, list),
        ("resultados_filtrados", resultados_filtrados, list),
        ("dashboard", dashboard, dict),
        ("insights", insights, dict),
        ("filtros_activos", filtros_activos, dict),
    )
    for campo, valor, tipo in colecciones:
        if not isinstance(valor, tipo):
            return campo
    if any(not isinstance(producto, dict) for producto in resultados_completos):
        return "resultados_completos"
    if any(not isinstance(producto, dict) for producto in resultados_filtrados):
        return "resultados_filtrados"
    return None


def _normalizar_contexto(contexto_usuario):
    if contexto_usuario is None:
        contexto_usuario = {}
    if not isinstance(contexto_usuario, dict):
        return None, "contexto_usuario", "el contexto del usuario es inválido."

    permitidos = {
        "presupuesto",
        "objetivo",
        "experiencia",
        "etapa_negocio",
        "tolerancia_riesgo",
    }
    desconocidos = sorted(set(contexto_usuario) - permitidos)
    if desconocidos:
        return (
            None,
            "contexto_usuario",
            f"se recibieron propiedades desconocidas: {', '.join(desconocidos)}.",
        )

    presupuesto = contexto_usuario.get("presupuesto")
    if presupuesto is not None:
        if (
            isinstance(presupuesto, bool)
            or not isinstance(presupuesto, (int, float))
            or presupuesto < 0
        ):
            return None, "presupuesto", "el presupuesto debe ser un número no negativo."
        presupuesto = float(presupuesto)

    objetivo = contexto_usuario.get("objetivo")
    if objetivo is not None:
        if not isinstance(objetivo, str) or not objetivo.strip():
            return None, "objetivo", "el objetivo debe ser texto no vacío."
        objetivo = objetivo.strip()

    experiencia = contexto_usuario.get("experiencia")
    if experiencia is not None:
        if not isinstance(experiencia, str):
            return None, "experiencia", "la experiencia es inválida."
        experiencia = experiencia.strip().casefold()
        if experiencia not in EXPERIENCIAS_PERMITIDAS:
            return None, "experiencia", "la experiencia es inválida."

    etapa = contexto_usuario.get("etapa_negocio")
    if etapa is not None:
        if not isinstance(etapa, str):
            return None, "etapa_negocio", "la etapa del negocio es inválida."
        etapa = etapa.strip().casefold()
        if etapa not in ETAPAS_PERMITIDAS:
            return None, "etapa_negocio", "la etapa del negocio es inválida."

    tolerancia = contexto_usuario.get("tolerancia_riesgo")
    if tolerancia is not None:
        if not isinstance(tolerancia, str):
            return None, "tolerancia_riesgo", "la tolerancia al riesgo es inválida."
        tolerancia = tolerancia.strip().casefold()
        if tolerancia not in TOLERANCIAS_PERMITIDAS:
            return None, "tolerancia_riesgo", "la tolerancia al riesgo es inválida."

    return (
        {
            "presupuesto": presupuesto,
            "objetivo": objetivo,
            "experiencia": experiencia,
            "etapa_negocio": etapa,
            "tolerancia_riesgo": tolerancia,
        },
        None,
        None,
    )


def _puntaje(producto):
    valor = producto.get("opportunity_score")
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if not 0 <= valor <= 100:
        return None
    return float(valor)


def _producto_prioritario(resultados):
    puntuados = [producto for producto in resultados if _puntaje(producto) is not None]
    if not puntuados:
        return None
    return max(
        puntuados,
        key=lambda producto: (_puntaje(producto), producto.get("roi", 0)),
    )


def _hay_opciones_similares(resultados):
    puntuados = sorted(
        (
            puntaje
            for puntaje in (_puntaje(producto) for producto in resultados)
            if puntaje is not None
        ),
        reverse=True,
    )
    return (
        len(puntuados) >= 2
        and puntuados[1] >= PUNTAJE_INTERESANTE
        and puntuados[0] - puntuados[1] <= DIFERENCIA_OPORTUNIDADES_SIMILARES
    )


def _datos_faltantes(contexto):
    faltantes = list(DATOS_COMERCIALES_AUSENTES)
    if contexto["presupuesto"] is None:
        faltantes.append("presupuesto disponible")
    if contexto["objetivo"] is None:
        faltantes.append("objetivo del usuario")
    if contexto["experiencia"] is None:
        faltantes.append("nivel de experiencia")
    if contexto["etapa_negocio"] is None:
        faltantes.append("etapa del negocio")
    if contexto["tolerancia_riesgo"] is None:
        faltantes.append("tolerancia al riesgo")
    return faltantes


def _nivel_confianza(datos_faltantes):
    if len(datos_faltantes) >= 4:
        return "bajo"
    if datos_faltantes:
        return "medio"
    return "alto"


def _agregar_unicos(destino, valores):
    destino.extend(valor for valor in valores if valor and valor not in destino)


def _integrar_comparacion_modelos(decision, comparacion, contexto):
    """Integra evidencia ya evaluada; no recalcula compatibilidad ni crea scores."""

    if not isinstance(comparacion, BusinessModelComparisonResult):
        raise DomainValidationError(
            "comparacion_modelos debe ser BusinessModelComparisonResult válido."
        )

    datos = {
        clave: list(valor) if isinstance(valor, list) else dict(valor)
        if isinstance(valor, dict)
        else valor
        for clave, valor in decision.items()
    }
    evaluaciones = comparacion.assessments
    compatibles = tuple(
        item
        for item in evaluaciones
        if item.compatibility in {"compatible", "compatible_con_condiciones"}
    )
    incompatibles = tuple(
        item for item in evaluaciones if item.compatibility == "incompatible"
    )
    indeterminados = tuple(
        item for item in evaluaciones if item.compatibility == "indeterminado"
    )
    restricciones_fuertes = tuple(
        (item, dimension)
        for item in evaluaciones
        for dimension in item.dimensions
        if dimension.evaluation == "incompatible"
    )

    _agregar_unicos(
        datos["evidencia_favorable"],
        (
            "Dato del Business Model Engine: "
            f"se evaluaron {len(evaluaciones)} modelos operativos con la versión "
            f"{comparacion.version}.",
        ),
    )
    for item in evaluaciones:
        _agregar_unicos(
            datos["evidencia_favorable"],
            (
                "Evaluación del Business Model Engine: "
                f"{item.business_model.name} = {item.compatibility}; "
                f"confianza {item.confidence.value}.",
            ),
        )
    for item, dimension in restricciones_fuertes:
        _agregar_unicos(
            datos["riesgos"],
            (
                f"{item.business_model.name}: {dimension.explanation} "
                f"(dimensión: {dimension.dimension}).",
            ),
        )
    _agregar_unicos(
        datos["datos_faltantes"],
        tuple(f"modelo operativo: {item}" for item in comparacion.missing_data),
    )
    _agregar_unicos(
        datos["reglas_aplicadas"],
        (
            "business_model_comparison_consumed",
            *(
                f"business_model_dimension:{dimension.dimension}"
                for item in evaluaciones
                for dimension in item.dimensions
                if dimension.evaluation in {"desfavorable", "incompatible", "desconocida"}
            ),
        ),
    )
    datos["contexto_utilizado"].update(
        {
            "business_model_comparison_id": comparacion.comparison_id,
            "business_model_comparison_version": comparacion.version,
            "business_model_confidence": comparacion.confidence.value,
            "business_models_considered": tuple(
                item.business_model.name for item in evaluaciones
            ),
            "business_model_under_consideration": (
                comparacion.consideration_model.name
                if comparacion.consideration_model
                else None
            ),
            "business_model_alternatives": tuple(
                item.name for item in comparacion.alternatives
            ),
            "business_model_relevant_dimensions": tuple(
                dict.fromkeys(
                    dimension.dimension
                    for item in evaluaciones
                    for dimension in item.dimensions
                    if dimension.evaluation
                    in {"desfavorable", "incompatible", "desconocida"}
                )
            ),
            "business_model_strong_restrictions": tuple(
                dimension.explanation
                for _, dimension in restricciones_fuertes
            ),
        }
    )
    _agregar_unicos(
        datos["limitaciones"],
        (
            "La comparación de modelos operativos orienta el próximo paso; no elige por el usuario.",
        ),
    )

    temas_educativos = tuple(
        dict.fromkeys(
            tema
            for item in evaluaciones
            for tema in item.educational_topics
        )
    )
    datos["contexto_utilizado"]["business_model_educational_topics"] = (
        temas_educativos
    )
    _agregar_unicos(
        datos["reglas_aplicadas"],
        tuple(
            f"business_model_educational_topic:{tema}"
            for tema in temas_educativos
        ),
    )
    beginner = bool(
        comparacion.simplified_for_beginner
        or contexto.get("experiencia") == "principiante"
    )

    if not evaluaciones or (indeterminados and len(indeterminados) == len(evaluaciones)):
        if datos["estado"] not in {"explorar", "posponer"}:
            datos["estado"] = "investigar"
        datos["proximo_paso"] = (
            "Siguiente paso sugerido: completar presupuesto, tiempo, logística, "
            "almacenamiento y preferencias antes de comparar modelos operativos."
        )
        _agregar_unicos(
            datos["reglas_aplicadas"],
            ("business_model_context_incomplete",),
        )
    elif incompatibles and len(incompatibles) == len(evaluaciones):
        if datos["estado"] != "explorar":
            datos["estado"] = "investigar"
        datos["proximo_paso"] = (
            "Siguiente paso sugerido: revisar las restricciones, el marketplace o la "
            "estrategia; la evaluación actual no conserva un modelo compatible."
        )
        _agregar_unicos(
            datos["reglas_aplicadas"],
            ("all_business_models_incompatible",),
        )
    elif comparacion.consideration_model is None and len(compatibles) >= 2:
        if datos["estado"] not in {"explorar", "posponer"}:
            datos["estado"] = "comparar"
        datos["proximo_paso"] = (
            "Siguiente paso sugerido: comparar las compensaciones de los modelos "
            "operativos sin declarar un ganador."
        )
        _agregar_unicos(
            datos["alternativas"],
            tuple(
                f"Mantener {item.business_model.name} como alternativa en estudio."
                for item in compatibles
            ),
        )
        _agregar_unicos(
            datos["reglas_aplicadas"],
            ("multiple_business_models_compare_tradeoffs",),
        )
    elif comparacion.consideration_model is not None:
        if datos["estado"] not in {"explorar", "posponer"}:
            datos["estado"] = "investigar"
        model = comparacion.consideration_model
        datos["proximo_paso"] = (
            "Siguiente paso sugerido: estudiar "
            f"{model.name} como opción de consideración y verificar sus requisitos, "
            "responsabilidades y restricciones antes de cualquier decisión."
        )
        _agregar_unicos(
            datos["evidencia_favorable"],
            (
                "Orientación del Business Model Engine: "
                f"{model.name} merece mayor consideración; no constituye una elección final.",
            ),
        )
        _agregar_unicos(
            datos["reglas_aplicadas"],
            ("business_model_for_further_study",),
        )
        _agregar_unicos(
            datos["alternativas"],
            tuple(
                f"Conservar {item.name} como alternativa para comparar."
                for item in comparacion.alternatives
            ),
        )
    elif any(item.compatibility == "compatible_con_condiciones" for item in evaluaciones):
        if datos["estado"] not in {"explorar", "posponer"}:
            datos["estado"] = "investigar"
        datos["proximo_paso"] = (
            "Siguiente paso sugerido: revisar las dimensiones que limitan el ajuste "
            "antes de considerar un modelo operativo."
        )
        _agregar_unicos(
            datos["reglas_aplicadas"],
            ("partially_compatible_business_model",),
        )

    if restricciones_fuertes:
        _agregar_unicos(
            datos["reglas_aplicadas"],
            ("strong_business_model_restriction_visible",),
        )
    parciales = tuple(
        item
        for item in evaluaciones
        if item.compatibility == "compatible_con_condiciones"
    )
    if parciales:
        _agregar_unicos(
            datos["reglas_aplicadas"],
            ("partially_compatible_business_model",),
        )
        _agregar_unicos(
            datos["riesgos"],
            tuple(
                f"{item.business_model.name}: {dimension.explanation} "
                f"(dimensión limitante: {dimension.dimension})."
                for item in parciales
                for dimension in item.dimensions
                if dimension.evaluation in {"desfavorable", "desconocida"}
            ),
        )
    if beginner and temas_educativos:
        datos["proximo_paso"] = (
            "Paso educativo sugerido antes de una decisión operativa: aprender "
            f"{temas_educativos[0]}. Después, {datos['proximo_paso'][0].lower()}"
            f"{datos['proximo_paso'][1:]}"
        )
        _agregar_unicos(
            datos["reglas_aplicadas"],
            ("business_model_beginner_education_first",),
        )

    if comparacion.confidence.value == "bajo":
        datos["nivel_confianza"] = "bajo"
        _agregar_unicos(
            datos["reglas_aplicadas"],
            ("business_model_low_confidence",),
        )
    elif comparacion.confidence.value == "medio" and datos["nivel_confianza"] == "alto":
        datos["nivel_confianza"] = "medio"

    datos["pregunta_de_continuacion"] = comparacion.continuation_question
    return datos


def _generar_decision_heredada(
    resultados_completos,
    resultados_filtrados,
    dashboard,
    insights,
    filtros_activos,
    contexto_usuario=None,
    comparacion_modelos=None,
):
    """Genera una orientación reproducible sin recalcular métricas financieras."""
    campo_invalido = _validar_entradas(
        resultados_completos,
        resultados_filtrados,
        dashboard,
        insights,
        filtros_activos,
    )
    if campo_invalido:
        return _error(campo_invalido, f"{campo_invalido} es inválido.")

    contexto, campo_contexto, mensaje_contexto = _normalizar_contexto(
        contexto_usuario
    )
    if campo_contexto:
        return _error(campo_contexto, mensaje_contexto)

    reglas = []
    evidencia = []
    riesgos = []
    alternativas = []
    condiciones = []
    datos_faltantes = _datos_faltantes(contexto)
    nivel_confianza = _nivel_confianza(datos_faltantes)
    total_completo = len(resultados_completos)
    total_filtrado = len(resultados_filtrados)
    prioritario = _producto_prioritario(resultados_filtrados)
    puntaje_prioritario = _puntaje(prioritario) if prioritario else None

    recomendables = [
        producto
        for producto in resultados_filtrados
        if producto.get("evaluacion") in CLASIFICACIONES_RECOMENDABLES
    ]

    evidencia.append(
        f"Dato: se muestran {total_filtrado} de {total_completo} productos analizados."
    )
    if prioritario:
        evidencia.append(
            "Estimación financiera: "
            f"{prioritario.get('nombre', 'La oportunidad principal')} obtiene "
            f"{puntaje_prioritario:.1f}/100 en Opportunity Score."
        )
    evidencia.append(
        "Supuesto: los costos y precios cargados por el usuario son correctos y siguen vigentes."
    )

    riesgos.extend(insights.get("riesgos_detectados", [])[:2])
    riesgos.append(
        "Faltan señales comerciales; una evaluación financiera favorable no confirma ventas."
    )

    if not resultados_completos:
        estado = "explorar"
        reglas.append("sin_resultados_explorar")
        recomendacion = "Carga productos válidos para comenzar la comparación."
        resumen = (
            "Todavía no hay resultados financieros. Oriva no puede priorizar una "
            "oportunidad sin datos calculados."
        )
        proximo_paso = "Carga una lista de productos con compra y venta estimadas."
        alternativas = [
            "Descargar la plantilla de ejemplo.",
            "Revisar qué datos necesita cada producto.",
        ]
        condiciones = ["Contar con al menos un producto válido y analizado."]
    elif not resultados_filtrados:
        estado = "posponer"
        reglas.append("sin_coincidencias_posponer")
        recomendacion = "Pospone la selección y revisa los criterios aplicados."
        resumen = (
            "Hay productos analizados, pero ninguno permanece visible con los filtros actuales."
        )
        proximo_paso = "Relaja un filtro a la vez y vuelve a comparar los resultados."
        alternativas = [
            "Revisar los filtros activos.",
            "Mantener los criterios y cargar más productos.",
        ]
        condiciones = ["Obtener al menos una coincidencia con los criterios definidos."]
    else:
        debil = (
            puntaje_prioritario is None
            or puntaje_prioritario < PUNTAJE_ANALIZAR_CON_CUIDADO
            or (
                not recomendables
                and puntaje_prioritario < PUNTAJE_INTERESANTE
            )
        )
        similares = _hay_opciones_similares(resultados_filtrados)
        favorable = (
            puntaje_prioritario is not None
            and puntaje_prioritario >= PUNTAJE_MUY_PROMETEDORA
        )

        if debil:
            estado = "posponer"
            reglas.append("resultados_debiles_posponer")
            recomendacion = "Pospone una inversión y busca alternativas más sólidas."
            resumen = (
                "Las estimaciones financieras actuales no ofrecen evidencia suficiente "
                "para priorizar una prueba."
            )
            proximo_paso = "Revisa costos, precios y nuevas alternativas antes de avanzar."
            alternativas = [
                "Corregir supuestos de costos.",
                "Comparar productos adicionales.",
            ]
            condiciones = [
                "Encontrar una oportunidad que supere los criterios financieros definidos."
            ]
        elif similares:
            estado = "comparar"
            reglas.append("oportunidades_similares_comparar")
            recomendacion = "Compara las oportunidades líderes antes de elegir cuál investigar."
            resumen = (
                "Las mejores opciones tienen puntuaciones financieras cercanas; el score "
                "por sí solo no produce una diferencia decisiva."
            )
            proximo_paso = "Compara demanda, competencia y proveedores de las opciones líderes."
            alternativas = [
                "Priorizar la opción con mayor margen.",
                "Priorizar la opción con menor exposición de capital.",
                "Mantener ambas en investigación.",
            ]
            condiciones = [
                "Obtener evidencia comercial que diferencie claramente las alternativas."
            ]
        elif favorable:
            estado = "investigar"
            reglas.extend(
                ["oportunidad_favorable", "datos_comerciales_ausentes"]
            )
            recomendacion = "Investiga la oportunidad antes de comprometer capital."
            resumen = (
                "La evaluación financiera es favorable, pero faltan demanda, competencia "
                "y condiciones reales de abastecimiento."
            )
            if contexto["presupuesto"] is not None:
                reglas.append("presupuesto_conocido_sin_habilitar_prueba")
                proximo_paso = (
                    "Diseñar una posible prueba pequeña y controlada después de confirmar "
                    "demanda, competencia, proveedor, costos finales y marketplace."
                )
            else:
                proximo_paso = (
                    "Confirma demanda, competencia, proveedor, costos finales y marketplace; "
                    "después define el presupuesto disponible."
                )
            alternativas = [
                "Comparar con la siguiente oportunidad del ranking.",
                "Solicitar cotizaciones a proveedores.",
                "Mantener la oportunidad en investigación.",
            ]
            condiciones = [
                "Verificar demanda y competencia.",
                "Confirmar proveedor, costos finales y marketplace.",
                "Definir un presupuesto antes de considerar cualquier prueba.",
            ]
            if contexto["presupuesto"] is not None and contexto["presupuesto"] <= PRESUPUESTO_BAJO:
                reglas.append("presupuesto_bajo")
                riesgos.append(
                    "El presupuesto es limitado y no habilita una prueba sin validación comercial."
                )
        else:
            estado = "investigar"
            reglas.append("evidencia_financiera_intermedia")
            recomendacion = "Investiga más antes de decidir si vale la pena realizar una prueba."
            resumen = (
                "Las estimaciones permiten continuar la evaluación, pero todavía no justifican "
                "una prueba sin información adicional."
            )
            proximo_paso = "Confirma costos y reúne señales comerciales comparables."
            alternativas = [
                "Comparar productos adicionales.",
                "Revisar los criterios financieros.",
                "Posponer hasta contar con más información.",
            ]
            condiciones = [
                "Mejorar la evidencia financiera o comercial de la oportunidad."
            ]

    if contexto["experiencia"] == "principiante":
        reglas.append("lenguaje_principiante")
        proximo_paso = f"Primer paso: {proximo_paso}"

    if nivel_confianza == "bajo":
        reglas.append("confianza_reducida_por_datos_faltantes")

    if contexto["presupuesto"] is None:
        pregunta = "¿Cuál es el presupuesto máximo que aceptarías usar en una prueba?"
    elif "demanda" in datos_faltantes:
        pregunta = "¿Qué evidencia de demanda puedes comprobar antes de avanzar?"
    else:
        pregunta = "¿Qué información nueva quieres incorporar a la siguiente decisión?"

    assert estado in ESTADOS_PERMITIDOS
    decision = {
            "estado": estado,
            "recomendacion_principal": recomendacion,
            "resumen": resumen,
            "evidencia_favorable": evidencia,
            "riesgos": list(dict.fromkeys(riesgos)),
            "datos_faltantes": datos_faltantes,
            "proximo_paso": proximo_paso,
            "alternativas": alternativas,
            "condiciones_para_avanzar": condiciones,
            "nivel_confianza": nivel_confianza,
            "reglas_aplicadas": list(dict.fromkeys(reglas)),
            "limitaciones": list(LIMITACIONES),
            "pregunta_de_continuacion": pregunta,
            "contexto_utilizado": contexto,
        }
    if comparacion_modelos is not None:
        try:
            decision = _integrar_comparacion_modelos(
                decision, comparacion_modelos, contexto
            )
        except DomainValidationError as error:
            return _error("comparacion_modelos", str(error))
    return resultado_exitoso(decision)


def generar_decision_dominio(
    analisis_completo,
    analisis_filtrado,
    dashboard,
    insights,
    filtros_activos,
    contexto_usuario=None,
    comparacion_modelos=None,
):
    """Consume contratos oficiales y conserva sin cambios las reglas vigentes."""
    if not isinstance(analisis_completo, AnalysisResult):
        raise DomainValidationError("analisis_completo debe ser AnalysisResult válido.")
    if not isinstance(analisis_filtrado, AnalysisResult):
        raise DomainValidationError("analisis_filtrado debe ser AnalysisResult válido.")

    completos = convertir_resultados_a_formato_actual(
        analisis_completo.opportunities
    )
    filtrados = convertir_resultados_a_formato_actual(
        analisis_filtrado.opportunities
    )
    respuesta = _generar_decision_heredada(
        completos,
        filtrados,
        dashboard,
        insights,
        filtros_activos,
        contexto_usuario,
        comparacion_modelos,
    )
    if not respuesta["exito"]:
        return respuesta

    prioritario = _producto_prioritario(filtrados)
    trazabilidad = list(analisis_filtrado.opportunities)
    ids_trazados = {
        item.opportunity.opportunity_id for item in trazabilidad
    }
    trazabilidad.extend(
        item
        for item in analisis_completo.opportunities
        if item.opportunity.opportunity_id not in ids_trazados
    )
    primary_opportunity_id = None
    if prioritario is not None:
        indice = filtrados.index(prioritario)
        primary_opportunity_id = (
            analisis_filtrado.opportunities[indice].opportunity.opportunity_id
        )
    contract = construir_recomendacion_dominio(
        respuesta["datos"],
        trazabilidad,
        primary_opportunity_id=primary_opportunity_id,
    )
    return resultado_exitoso(contract)


def generar_decision(
    resultados_completos,
    resultados_filtrados,
    dashboard,
    insights,
    filtros_activos,
    contexto_usuario=None,
    comparacion_modelos=None,
):
    """Mantiene el contrato heredado de la UI sobre el flujo oficial de dominio."""
    campo_invalido = _validar_entradas(
        resultados_completos,
        resultados_filtrados,
        dashboard,
        insights,
        filtros_activos,
    )
    if campo_invalido:
        return _error(campo_invalido, f"{campo_invalido} es inválido.")

    analisis_completo = construir_analisis_decision(
        resultados_completos,
        analysis_id="decision-completo",
    )
    analisis_filtrado = construir_analisis_decision(
        resultados_filtrados,
        analysis_id="decision-filtrado",
    )
    respuesta = generar_decision_dominio(
        analisis_completo,
        analisis_filtrado,
        dashboard,
        insights,
        filtros_activos,
        contexto_usuario,
        comparacion_modelos,
    )
    if not respuesta["exito"]:
        return respuesta
    if not isinstance(respuesta["datos"], DecisionRecommendation):
        raise DomainValidationError("El Decision Engine no devolvió su contrato oficial.")
    return resultado_exitoso(
        convertir_recomendacion_a_formato_actual(respuesta["datos"])
    )
