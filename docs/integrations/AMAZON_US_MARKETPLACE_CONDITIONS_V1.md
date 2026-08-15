# Amazon US Marketplace Conditions Capability V1

## Victoria vertical

Oriva puede resolver una necesidad de investigación de categoría `marketplace`
consultando una fuente pública oficial, conservar procedencia y momento de
consulta, normalizar el resultado como `EvidenceRecord` y devolverlo mediante
el puerto genérico `ResearchCapability`.

La pregunta V1 es deliberadamente única:

> ¿Cuáles son las tarifas base de los planes de venta de Amazon US?

La fuente allowlisted es `https://sell.amazon.com/pricing?mons_sel_locale=en_US`.
La evidencia contiene USD 0.99 por artículo vendido para Individual y USD 39.99
por mes para Professional, únicamente cuando ambos valores aparecen con la
estructura esperada en la página oficial.

## Límites

- Región: US.
- Marketplace: `amazon-us`.
- Categoría: `marketplace`.
- Subjects: `business_path` o `marketplace`.
- Información pública; no usa autenticación ni datos de cuenta.
- No incluye referral fees, FBA, almacenamiento, publicidad, impuestos,
  promociones ni recomendaciones de plan.
- No modifica Core, fórmulas financieras, Opportunity Graph ni Decision Engine.

## Seguridad y trazabilidad

El transporte solo acepta HTTPS y el host `sell.amazon.com`, valida redirects y
tipo de contenido, limita la respuesta a 2 MB y aplica timeout. La evidencia
conserva URL, `retrieved_at`, `observed_at` y SHA-256 de los valores semánticos
normalizados (`condition_type`, moneda, importes y bases de cobro). Cambios
puramente visuales del HTML no alteran esa huella; cambios materiales en las
tarifas sí. La fecha de consulta sigue formando parte de la identidad histórica
del `EvidenceRecord`.
Nunca almacena headers, cookies, credenciales ni cuerpo HTML completo.

## Semántica de error

Timeout, indisponibilidad, respuesta HTTP, redirect inesperado o cambio de
formato producen `ResearchFailure`. No producen `EvidenceRecord`, `NO_DATA` ni
una conclusión comercial negativa. El parser falla cerrado si no puede
corroborar ambos importes.

## Freshness y verificación

Una lectura parseada desde el dominio oficial se marca `VERIFIED`, `CURRENT` y
confianza alta en el momento de consulta. La limitación registra que la fuente
no expone una fecha efectiva estructurada. Una política futura deberá expirar o
refrescar la captura; V1 no inventa una fecha efectiva.

## Extensión posterior

Referral fees, restricciones, FBA y otros marketplaces requieren preguntas,
parsers y pruebas independientes. No deben ampliar silenciosamente esta
capability.
