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
