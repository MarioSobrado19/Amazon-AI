# Commercial Discovery Source Acquisition V1

> **INTERNAL / CONFIDENTIAL — ORIVA.** Revisión fechada 2026-08-20. Este
> documento evalúa legitimidad y utilidad técnica; no autoriza compras,
> inventario, listings, contacto comercial ni uso de credenciales externas.

## Decisión

USDA FoodData Central se adopta como primera fuente vertical de identidad
comercial real para Discovery V1, limitada a alimentos de marca declarados para
Estados Unidos. Su `DEMO_KEY` está publicada expresamente para exploración
inicial, con 30 solicitudes/hora y 50/día por IP. Los datos son dominio público
publicados bajo CC0 y USDA solicita atribución.

La fuente aporta `catalog_presence`: FDC ID, GTIN/UPC cuando existe, descripción,
marca, categoría, país de mercado, fuente interna y fechas. No es marketplace y
no acredita precio, disponibilidad, demanda, ventas, competencia, proveedor,
elegibilidad, margen ni rentabilidad. Por ello una señal USDA aislada queda
`surfaced`, nunca `research_ready`.

Fuentes oficiales principales:

- USDA API Guide: https://fdc.nal.usda.gov/api-guide/
- USDA data/licencia: https://fdc.nal.usda.gov/
- USDA Branded Foods: https://fdc.nal.usda.gov/GBFPD_Documentation/
- USDA downloads: https://fdc.nal.usda.gov/download-datasets/

## Matriz explicable

No se aplica score ni ponderación oculta.

| Fuente | Estado | Acceso/legitimidad | US e identidad | Señales y freshness | Coste/límites | Retención/derivados | Utilidad y límite para Oriva |
|---|---|---|---|---|---|---|---|
| USDA FoodData Central Branded API | **AVAILABLE_NOW** | API oficial; `DEMO_KEY` oficial para exploración, sin cuenta | `marketCountry=US`, FDC ID, GTIN/UPC, marca y categoría | catálogo alimentario; API Branded mensual; observación fechada al request | sin coste publicado; demo 30/h y 50/día, key propia 1,000/h por IP | CC0/dominio público; atribución solicitada | primera identidad real y reproducible; alimentos solamente; no demanda/precio/ventas |
| USDA Branded downloadable dataset | **AVAILABLE_NOW** | descarga oficial sin credencial | cobertura Branded global filtrable a US; archivos muy grandes | releases descargables abril/octubre, API más reciente entre releases | sin coste; abril 2026 ~195 MB JSON comprimido | CC0; snapshot versionable | útil para lote futuro; excesivo para smoke V1 y menos fresco que API |
| Open Food Facts | **AVAILABLE_WITH_HUMAN_ACTION** | lecturas sin auth, pero documentación pide leer términos y completar formulario de uso | barcodes, nombres, marcas, categorías y países; cobertura colaborativa | catálogo comunitario; exactitud/completitud no garantizadas | gratis; search 10/min/IP, product read 15/min/IP | ODbL/DbCL y CC BY-SA para imágenes; atribución/share-alike requieren revisión | buena corroboración futura de alimentos; no se usa antes de revisión humana de licencia/formulario |
| Best Buy Products/Categories API | **AVAILABLE_WITH_HUMAN_ACTION** | email + API key y aceptación de términos | catálogo US, SKU, categoría, precio, disponibilidad y atributos | precios casi en tiempo real; catálogo actual/histórico | coste no confirmado; límite asignado no publicado claramente | contenido solo puede cachearse temporalmente; enlaces expiran en 7 días | fuerte para electrónica; requiere acción humana y diseño de retención conforme |
| Kroger Public Products API | **AVAILABLE_WITH_HUMAN_ACTION** | cuenta, registro de aplicación y OAuth2 client credentials | catálogo US, product ID/UPC, marca; precio/aisle con location ID | catálogo/producto y disponibilidad por tienda cuando se filtra | 10,000 llamadas/día publicadas para Products; coste no confirmado | términos y uso comercial deben aceptarse al registrar la app | candidato fuerte para grocery retail real; más comercial que USDA, pero requiere cuenta/secreto |
| Walmart Marketplace Item Search | **AVAILABLE_WITH_HUMAN_ACTION** | vendedor Marketplace o Solution Provider aprobado + token | catálogo Walmart US, keyword/UPC/GTIN/ASIN; hasta 40 coincidencias | items publicados; disponibilidad implícita limitada al estado publicado | throttling según integración; coste no confirmado | sujeto a acuerdos Marketplace y acceso del seller/provider | identidad comercial fuerte, pero acceso no es público ni apropiado sin relación aprobada |
| Walmart Connect Top Search Trends | **PENDING_EXTERNAL_APPROVAL** | exclusivo de Walmart Connect Partner Network | keywords US y top 3 items asociados | diario, ventana móvil 7 días; sí contiene búsquedas/unidades agregadas según documentación | onboarding partner; límites por integración | términos de partner/advertiser | señal comercial muy valiosa, pero no disponible sin aprobación contractual |
| Amazon SP-API Catalog Items | **PENDING_EXTERNAL_APPROVAL** | app SP-API, roles y autorización de selling partner | ASIN, catálogo, clasificación y atributos en Amazon US | catálogo; pricing/fees requieren operaciones y roles adicionales | usage plans por operación; coste no confirmado | políticas SP-API y datos de seller; secretos obligatorios | fuerte identidad Amazon, pero no es acceso público y no debe usarse sin onboarding aprobado |
| Amazon Creators/Associates API | **NOT_SUITABLE** | programa Associates y requisitos de actividad/ventas | productos/ofertas Amazon según acceso concedido | catálogo/ofertas, no ventas de mercado | cuota ligada a cuenta; coste no confirmado | licencia Associates, uso orientado a referrals | circular para Caso #0001 pre-venta y no fuente neutral de discovery general |
| Google Merchant API / Shopping trends | **NOT_SUITABLE** | Merchant Center + OAuth; insights dependen del inventario y elegibilidad de la cuenta | datos del propio merchant/categorías relacionadas | productos propios y tendencias elegibles; no catálogo público universal | cuotas por cuenta; coste no confirmado | Merchant Center terms | útil después de operar catálogo propio, no para descubrir oportunidades desde cero |
| Google Trends API Alpha | **PENDING_EXTERNAL_APPROVAL** | solicitud y aceptación como tester Alpha | términos/temas y región US, sin identidad comercial fuerte | interés de búsqueda, hasta cinco años, intervalos regulares | cuota/coste no confirmados | condiciones Alpha | corroboración futura de `search_interest`; no catálogo, ventas ni conversión |
| eBay Browse API | **PENDING_EXTERNAL_APPROVAL** | Production Buy APIs restringidas, contratos y Growth Check | listings eBay US, item IDs, producto, categoría y precios anunciados | oferta observable al request | límites de aplicación; coste no confirmado | Buy API requirements, API License y compliance | excelente corroboración comercial futura; **HOLD** por ticket 260819-000066 y sin Production |
| Etsy Open API v3 | **AVAILABLE_WITH_HUMAN_ACTION** | Personal App con revisión; Commercial Access posterior para escala | listings/identidad Etsy, cobertura sectorial | listings activos, no ventas; freshness al request | límites por app; coste no confirmado | caching/API Terms; no scraping; atribución de marca requerida | útil para handmade/digital; requiere app y revisión humana del caso comercial |
| Census MRTS/Trade, BLS, BEA, Data.gov | **NOT_SUITABLE** como primaria | fuentes gubernamentales legítimas; algunas requieren key | US, generalmente categoría/macro, no identidad de producto | actividad, precios o metadatos agregados | normalmente gratuito; cuotas variables | datos públicos según dataset | complementan `category_activity`/macro; no crean producto comercial por sí solos |
| APIs privadas/no documentadas de retailers y scraping | **PROHIBITED/UNACCEPTABLE** | sin autorización contractual o endpoint público estable | cobertura aparente pero no defendible | semántica y freshness no garantizadas | riesgo operativo/legal alto | almacenamiento y derivados no autorizados | no se usarán; tampoco browser automation ni reverse engineering |
| Target u otros retailers sin API pública oficial verificable | **UNRESOLVED** | no se verificó una superficie oficial adecuada | no confirmado | no confirmado | no confirmado | no confirmado | permanecer fuera hasta documentación primaria inequívoca |

## Arquitectura implementada

```text
USDA FoodData Central Branded Search
        ↓ HTTPS POST, allowlist, timeout, retry y límite 5
UsdaFoodDataCentralDiscoverySource
        ↓ schema validation + field allowlist
DiscoverySignal(CATALOG_PRESENCE, REAL)
        ↓ pipeline existente de Sprint 42
OpportunityHypothesis(SURFACED)
        ↓
ResearchNeeds explícitos; Caso #0001 continúa HOLD
```

El adapter no conserva el JSON crudo, ingredientes ni nutrientes. Extrae solo
identidad y contexto necesarios. `NO_DATA` permanece distinto de
`TECHNICAL_FAILURE`; 429/5xx/timeouts son fallos reintentables y nunca “sin
oportunidad”. La respuesta serializada no contiene la clave de acceso, aunque
`DEMO_KEY` sea un identificador público de documentación y no un secreto.

## Gates y siguientes accesos humanos

No se necesita cuenta para el smoke USDA con `DEMO_KEY`. Para uso sostenido:

1. abrir https://api.data.gov/signup/;
2. solicitar una key para FoodData Central;
3. guardarla únicamente como secreto local, nunca en Git, logs o reportes;
4. sustituir `DEMO_KEY` mediante configuración segura en un sprint aprobado;
5. conservar atribución a USDA y límites efectivos de headers.

Ese paso desbloquearía mayor cuota, no una semántica comercial más fuerte. Para
corroboración retail real, el siguiente acceso humano con mejor relación entre
valor y complejidad es registrar una aplicación Kroger o solicitar una API key
de Best Buy, después de revisar sus términos de almacenamiento y uso comercial.

## eBay y Caso #0001

- Ticket eBay: `260819-000066`.
- Estado: `HOLD — EXTERNAL COMPLIANCE CONFIRMATION PENDING`.
- No exención, Production credentials, Browse Production ni Growth Check.
- Sandbox sigue siendo validación técnica, nunca evidencia comercial.
- Capital máximo futuro: USD 750.
- Capital autorizado, gastado y en riesgo: USD 0.
- `current_candidates` sigue vacío.

El smoke USDA puede producir identidades reales `surfaced`, pero una sola señal
de catálogo no satisface el gate de dos señales no redundantes ni demuestra una
oportunidad investigable completa. No se promueve nada a Opportunity,
CandidateBusinessPath, BusinessPath, compra o inversión.

## Riesgos y candidatos internos de IP

- Riesgo de sesgo sectorial: USDA cubre alimentos, no el universo de e-commerce.
- Riesgo de relevancia: búsqueda textual puede devolver coincidencias amplias;
  FDC ID/GTIN conserva identidad, pero se necesita revisión/corroboración.
- Riesgo de stale data: presencia FDC no equivale a disponibilidad actual.
- Riesgo semántico: nunca convertir totalHits o posición de búsqueda en demanda.
- Candidato interno de IP: composición explicable de identidades oficiales con
  señales comerciales posteriores y gates semánticos sin score. Esto no afirma
  novedad jurídica ni patentabilidad.
