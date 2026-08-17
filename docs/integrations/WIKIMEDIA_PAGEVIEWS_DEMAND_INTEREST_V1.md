# Wikimedia Pageviews Demand Interest Capability V1

## Señal exacta

V1 responde una pregunta deliberadamente estrecha:

> ¿Cuántas vistas diarias registró un artículo exacto de Wikipedia en un periodo histórico completo?

La fuente primaria es la API pública oficial Wikimedia Analytics, endpoint
`pageviews/per-article`. La consulta fija:

- proyecto: `en.wikipedia.org`;
- acceso: `all-access`;
- agente: `user` (excluye tráfico clasificado como `spider` o `automated`);
- granularidad: `daily`;
- título exacto del artículo en `subject_id`;
- periodo inclusivo en `time_scope` con formato `YYYY-MM-DD/YYYY-MM-DD`.

Fuentes oficiales consultadas:

- [Referencia oficial de Page View Analytics](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html)
- [Concepto oficial de page view](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/concepts/page-views.html)
- [Política oficial de acceso y User-Agent](https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy)

La evidencia conserva cada observación diaria y su suma aritmética exacta. No
calcula score, ranking, tendencia, forecast ni recomendación.

V1 requiere que el caller suministre explícitamente
`subject_type=wikipedia_article` y el título exacto. No convierte nombres de
productos en artículos, no busca sinónimos y no realiza entity resolution. Que
exista el artículo `Headphones` no demuestra que represente el producto
comercial que el usuario investiga.

El path del endpoint usa `en.wikipedia.org`; la respuesta oficial identifica
ese mismo proyecto como `en.wikipedia`. V1 conserva y valida ambos valores por
separado, sin aceptar alias adicionales.

## Qué NO mide

Las page views son una señal indirecta de atención al contenido. No equivalen a
y V1 no las presenta como:

- búsquedas o volumen de keywords;
- demanda comercial demostrada;
- intención de compra;
- ventas, unidades, ingresos o conversión;
- personas únicas;
- tamaño de mercado;
- probabilidad de éxito o recomendación de inversión.

Un aumento o descenso puede deberse a noticias, estacionalidad, enlaces,
cambios editoriales u otros eventos. Un título puede ser ambiguo, y redirects o
títulos alternativos pueden repartir la atención. Esta señal debe contrastarse
en el futuro con fuentes de otra naturaleza, siempre como evidencias separadas.

## Alcance geográfico y marketplace

El endpoint por artículo usado por V1 no devuelve ubicación de lectores. Por
eso `region` y `marketplace_id` deben ser `None`; la evidencia registra
`geographic_scope=not_geolocated`. La edición inglesa es un proyecto lingüístico,
no una región comercial ni una aproximación a Amazon US.

Por ello esta evidencia no puede cerrar una pregunta que exija demanda de US,
NY, Amazon US u otro marketplace o región. Solo puede cubrir una pregunta
compatible sobre vistas o atención histórica del artículo explícito.

## Provenance, verificación y freshness

Cada `EvidenceRecord` incluye fuente, URL HTTPS allowlisted, `retrieved_at` UTC,
periodo observado UTC, proyecto, parámetros de la consulta, tipo `DATA`, estado
`VERIFIED`, freshness `CURRENT`, versión de capability/parser y SHA-256 de la
serie semántica normalizada. La huella cambia si cambian observaciones o
parámetros, pero no por el orden visual de las claves JSON. Recuperaciones en
momentos distintos conservan identidades históricas distintas.

`VERIFIED` significa que la respuesta coincide exactamente con el contrato de
la API oficial; no verifica causalidad comercial. `CURRENT` describe la captura
vigente de un periodo histórico completo y no promete inmutabilidad eterna del
dataset. Una política futura podrá refrescar o expirar capturas.

Que el periodo histórico haya terminado no vuelve falsa ni expirada la
observación. Su relevancia para una decisión presente es una evaluación
distinta que esta capability no realiza.

## Seguridad y adquisición

Solo se permite HTTPS, host `wikimedia.org`, puerto estándar y la ruta del
endpoint aprobado. Los redirects se validan antes de aceptar contenido. Hay
timeout, límite de 1 MB, tipo `application/json` obligatorio y User-Agent
descriptivo. No usa credenciales, cookies, sesiones privadas, Seller Central,
SP-API ni PII, y no persiste el cuerpo JSON completo.

El User-Agent identifica `Oriva/1.0` y utiliza la URL pública del repositorio
como contacto, siguiendo el formato recomendado por Wikimedia.

## Fallos y NO_DATA

- timeout, red/DNS, HTTP no concluyente o `429/5xx`: `ResearchFailure` técnico;
- redirect no permitido o fuente no allowlisted: `ResearchFailure` de seguridad;
- JSON inválido, campos cambiados, observaciones duplicadas, incompatibles o
  días faltantes: `ResearchFailure` conservador;
- `404` oficial o `items=[]`: `NO_DATA`, sin `EvidenceRecord`.

`NO_DATA` significa únicamente que esta consulta no obtuvo observaciones
oficiales verificables. Nunca se convierte en cero vistas, ausencia de demanda o
ausencia de ventas.

## Pruebas y smoke check

La suite normal usa fixtures locales y fetchers inyectados; no toca Internet.
Los valores de los fixtures son sintéticos y existen únicamente para validar el
contrato del parser; no representan atención, demanda ni ventas reales.
La consulta real está separada en:

`python3 -m tests.smoke_wikimedia_demand_interest`

El smoke consulta únicamente tres días históricos completos del artículo
`Headphones` y muestra el `ResearchCapabilityResult` trazable.
