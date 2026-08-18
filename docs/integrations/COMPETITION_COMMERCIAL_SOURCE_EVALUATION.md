# Competition Research V1 — evaluación de fuentes comerciales

## Conclusión

Competition Research necesita observar oferta comercial real. El experimento de
Library of Congress queda fuera del flujo. La recomendación para la primera
capability comercial es **eBay Browse API**, condicionada a una decisión humana
de registrar Oriva y custodiar credenciales de producción.

No se implementó cliente eBay ni Amazon, no se crearon credenciales y no se
realizaron consultas autenticadas.

## Comparación

| Camino | Datos potenciales | Autenticación | Tiempo relativo | Calidad comercial | Coste confirmado | Riesgo/mantenimiento |
| --- | --- | --- | --- | --- | --- | --- |
| eBay Browse API | Listings observables, item ID, título, precio/moneda, condición, categoría, vendedor cuando el contrato lo entregue, ubicación y opciones comerciales; búsqueda por keyword, categoría, GTIN, producto, imagen y filtros | OAuth Client Credentials; Application Access Token y scope Buy API. Requiere cuenta y keyset de producción | Bajo–medio después de aprobación | Alta para eBay, región/marketplace explícitos | No se confirmó una tarifa por llamada en esta revisión; sí existen costes internos de registro, custodia de secretos, operación y cumplimiento. Debe verificarse en el portal antes de producción | Tokens, límites, políticas de Buy API y cambios de contrato |
| Amazon SP-API | Catálogo mediante `searchCatalogItems`; según APIs/roles adicionales, detalles, restricciones, pricing y ofertas | Registro SP-API, perfil/rol, aplicación, LWA client ID/secret y autorización de selling partner; access/refresh tokens según operación | Medio–alto | Alta para Amazon, pero fragmentada entre APIs y permisos | No se confirmó una tarifa por llamada; pueden existir costes de cuenta, operación, revisión y cumplimiento según el modelo elegido. Debe confirmarse durante onboarding | Onboarding, revisión, seguridad de secretos, roles y usage plans dinámicos |
| Otra API oficial de marketplace | Debe verificarse por marketplace; Etsy Open API v3 es candidata para estudiar listings activos, pero su contrato, permisos, campos comparables y condiciones de uso requieren una revisión separada antes de elegirla | API key y, según endpoint/scope, OAuth; pendiente de validación contractual exacta | Incierto | Potencialmente útil, con alcance más especializado que eBay | Desconocido hasta validar el programa y sus términos oficiales | Riesgo de alcance limitado, permisos insuficientes o términos incompatibles |
| Supplier primero | Cotizaciones, MOQ, disponibilidad, coste, lead time y términos de abastecimiento si se integra un proveedor legítimo | Normalmente cuenta/API o acuerdo con proveedor | Variable; puede ser rápido con un proveedor elegido | Evidencia comercial real, pero resuelve abastecimiento, no competencia | Dependiente del proveedor, contrato, plan de API y negociación comercial | Integraciones heterogéneas y datos privados/comerciales |

## eBay Browse API

Fuente oficial:

- [Browse API overview](https://developer.ebay.com/api-docs/buy/browse/overview.html)
- [Search item summaries](https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search)
- [OAuth Client Credentials Grant](https://developer.ebay.com/api-docs/static/oauth-client-credentials-grant.html)
- [API call limits](https://developer.ebay.com/develop/get-started/api-call-limits)

El flujo propuesto es server-to-server:

1. crear cuenta de developer y keyset de producción;
2. mantener client ID y client secret fuera de Git;
3. solicitar un **Application Access Token** con Client Credentials y el scope
   general de Buy API;
4. llamar `item_summary/search` con marketplace explícito mediante
   `X-EBAY-C-MARKETPLACE-ID`;
5. conservar únicamente campos necesarios y snapshots versionados;
6. respetar límites asignados, expiración del token, 429 y backoff.

El Application Access Token representa a la aplicación, no a un usuario eBay,
y permite operaciones públicas compatibles con ese grant. No debe usarse para
datos privados de cuenta. El contrato definitivo, campos disponibles, límites
y permisos deben verificarse en el portal de producción al registrar la app;
las páginas oficiales estuvieron bloqueadas por el CDN desde este entorno
durante esta revisión, por lo que no se fija silenciosamente una cuota numérica.

Una futura evidencia deberá conservar, cuando estén disponibles: item ID,
título, URL, precio y moneda, condición, categoría, marca/vendedor conforme al
contrato, ubicación, marketplace, región, consulta/filtros, fetched_at, fuente,
versión, freshness y limitaciones. El número de resultados no debe convertirse
automáticamente en “competencia alta” o “baja”.

## Amazon SP-API

Fuentes oficiales:

- [Catalog Items API](https://developer-docs.amazon.com/sp-api/docs/catalog-items-api-v2022-04-01-reference)
- [Conexión a SP-API](https://developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api)
- [Registro de aplicación](https://developer-docs.amazon.com/sp-api/docs/registering-your-application)
- [Roles](https://developer-docs.amazon.com/sp-api/docs/roles-in-the-selling-partner-api)
- [Usage plans y límites](https://developer-docs.amazon.com/sp-api/docs/usage-plans-and-rate-limits)

`searchCatalogItems` permite buscar el catálogo con marketplace IDs y criterios
como keywords o identificadores. Sin embargo, catálogo no equivale por sí mismo
a oferta competitiva completa. Precios, ofertas y restricciones pueden requerir
Product Pricing, Listings Restrictions u otras APIs, roles y autorizaciones.

El onboarding requiere decidir aplicación pública o privada, registrar perfil y
roles, crear credenciales LWA, implementar autorización y custodiar client
secret, access tokens y refresh tokens. Los usage plans pueden depender del par
aplicación–selling partner y Amazon recomienda manejar 429 con backoff y el
header de límite cuando esté disponible.

No se usará scraping de Amazon Search ni se crearán credenciales sin aprobación.

## Otra fuente oficial candidata

Etsy Open API v3 merece una investigación posterior como fuente oficial de un
marketplace especializado. No se selecciona en este sprint: antes habría que
confirmar en su documentación y programa de desarrolladores qué endpoint de
listings activos es accesible para Oriva, qué scopes exige, qué campos entrega,
qué límites y costes aplican y si sus términos permiten conservar snapshots
comparables. No se asumirá que una API key u OAuth conceden acceso a cualquier
dato.

Fuente oficial para esa evaluación futura:

- [Etsy Open API v3](https://developers.etsy.com/documentation/)

## Recomendación

**Opción A: registrar Oriva como developer app y comenzar con eBay Browse API.**

Es el camino más corto hacia listings comerciales observables con marketplace,
región, identificadores y precios explícitos. Permite validar primero los
contratos, seguridad, snapshots y semántica de Competition Research sin asumir
el onboarding más amplio de Amazon.

Amazon debe continuar inmediatamente después como integración estratégica, no
como atajo. Supplier-first solo debe desplazar eBay si el objetivo prioritario
cambia de observar competencia a validar abastecimiento y ya existe un proveedor
con API o datos autorizados.

## Decisiones humanas pendientes

1. Autorizar o no el registro de una cuenta eBay Developers para Oriva.
2. Decidir si el primer uso será sandbox y luego producción.
3. Aprobar dónde se custodiarán client ID/secret y tokens; nunca en Git.
4. Definir marketplace inicial, recomendado `EBAY_US`, y categorías piloto.
5. Revisar y aceptar términos, requisitos de Buy API y límites asignados.
6. Decidir cuándo iniciar en paralelo el onboarding Amazon SP-API.
7. Elegir aplicación Amazon pública o privada y los roles estrictamente mínimos.
