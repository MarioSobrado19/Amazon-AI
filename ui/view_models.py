"""Transformaciones de contratos de aplicación para la interfaz."""


PLANTILLA_CSV = b"""nombre,costo,precio
Organizador de cocina,8,29.99
Botella deportiva,11,34.99
Luz LED para escritorio,15,49.99
Soporte para laptop,18,44.99
Mouse inal\xc3\xa1mbrico,7,24.99
Tapete para escritorio,4,19.99
Organizador de cables,3,15.99
Cargador USB-C,12,39.99
"""


def mensajes_de_error(resultado):
    return [
        error.get("mensaje", "No se pudo completar la operación.")
        for error in resultado.get("errores", [])
    ]


def preparar_filas(productos):
    return [
        {
            "Nombre": producto["nombre"],
            "Costo": producto["costo"],
            "Precio": producto["precio"],
        }
        for producto in productos
    ]


def preparar_resultados(productos):
    return [
        {
            "Posición": posicion,
            "Producto": producto["nombre"],
            "Precio": producto["precio"],
            "Costo total": producto["costo_total"],
            "Ganancia": producto["ganancia"],
            "Margen %": producto["margen"],
            "ROI %": producto["roi"],
            "Evaluación": producto["evaluacion"],
        }
        for posicion, producto in enumerate(productos, start=1)
    ]


def preparar_estado_filtros(filtros=None):
    filtros = dict(filtros or {})
    numericos = (
        "roi_minimo",
        "margen_minimo",
        "ganancia_minima",
        "precio_maximo",
    )
    return {
        "activos": {nombre: nombre in filtros for nombre in numericos},
        "valores": {
            nombre: float(filtros.get(nombre, 0.0)) for nombre in numericos
        },
        "texto_nombre": filtros.get("texto_nombre", ""),
    }


def construir_filtros(estado_filtros):
    filtros = {
        nombre: estado_filtros["valores"][nombre]
        for nombre, activo in estado_filtros["activos"].items()
        if activo
    }
    texto = estado_filtros.get("texto_nombre", "").strip()
    if texto:
        filtros["texto_nombre"] = texto
    return filtros
