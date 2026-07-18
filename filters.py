import unicodedata


def _normalizar_texto(texto):
    texto_normalizado = unicodedata.normalize("NFKD", texto)
    texto_sin_acentos = "".join(
        caracter
        for caracter in texto_normalizado
        if not unicodedata.combining(caracter)
    )
    return texto_sin_acentos.casefold()


def filtrar_productos(
    productos,
    roi_minimo=None,
    margen_minimo=None,
    ganancia_minima=None,
    precio_maximo=None,
    texto_nombre=None,
):
    """Devuelve productos que cumplen todos los criterios proporcionados."""
    if not productos:
        return []

    texto_buscado = None
    if texto_nombre is not None:
        texto_buscado = _normalizar_texto(texto_nombre.strip())

    resultados = []

    for producto in productos:
        if roi_minimo is not None and producto["roi"] < roi_minimo:
            continue
        if margen_minimo is not None and producto["margen"] < margen_minimo:
            continue
        if ganancia_minima is not None and producto["ganancia"] < ganancia_minima:
            continue
        if precio_maximo is not None and producto["precio"] > precio_maximo:
            continue
        if texto_buscado and texto_buscado not in _normalizar_texto(producto["nombre"]):
            continue

        resultados.append(producto)

    return resultados
