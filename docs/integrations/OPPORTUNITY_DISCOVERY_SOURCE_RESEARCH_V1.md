# Opportunity/Product Discovery V1 — investigación de fuentes

> **INTERNAL / CONFIDENTIAL — ORIVA.** Investigación fechada 2026-08-19.
> No autoriza cuentas, acuerdos, credenciales, pagos, scraping, inversión ni
> publicación. Los enlaces son documentación oficial primaria consultada; los
> límites no publicados se registran como `NO_DATA`, no se estiman.

## Conclusión ejecutiva

Discovery V1 puede construirse sin esperar a eBay, pero no puede producir hoy
hipótesis comerciales reales únicamente con fuentes sin credenciales. Census
MRTS/International Trade, BLS/BEA y Wikimedia pueden generar semillas y contexto;
ninguna demuestra demanda de producto. La primera combinación operativa
recomendada es:

1. **Census MRTS + International Trade** para cambios de categoría/importación;
2. **Wikimedia Pageviews** ya integrada, solo como atención indirecta;
3. **Best Buy Products/Categories**, tras aprobación humana de cuenta/API key y
   revisión de términos, para identidad de catálogo, precio y presencia retail;
4. **una segunda corroboración comercial autorizada** —preferentemente eBay
   Browse cuando se desbloquee; alternativamente Walmart Marketplace Item Search
   si Oriva llega a ser seller/solution provider aprobado— antes de emitir una
   `OpportunityHypothesis` real.

Hasta que exista el punto 3 o 4, el sistema puede producir `DiscoverySeed`, no
hipótesis. Google Trends Alpha es excelente candidato futuro de `search_interest`,
pero su acceso sigue limitado; Google Ads Keyword Ideas requiere cuenta, OAuth y
developer token y su métrica describe búsqueda publicitaria, no ventas.

## Matriz comparativa

`Ahora` significa sin nueva credencial humana. Coste solo se afirma cuando la
fuente oficial lo publica; en los demás casos es **no confirmado**.

| Fuente / producto exacto | Señal y granularidad | US / freshness | Acceso, entorno, cuota y coste | TOS, retención y derivación | Utilidad / límite inferencial | Riesgo / integración / ahora |
|---|---|---|---|---|---|---|
| Amazon Associates **Creators API**: `SearchItems`, `GetItems`, `GetVariations`, `GetBrowseNodes` | catálogo, categoría, producto, precio/oferta cuando el recurso lo expone | US; actualidad del catálogo, SLA no confirmado | Associates + 10 ventas calificadas/30 días + registro + OAuth; production; cuota asignada por cuenta; coste no confirmado | licencia de Associates; almacenamiento/derivación solo dentro de términos aprobados, no confirmado para corpus analítico | Buena identidad/catálogo; no prueba ventas, margen ni oportunidad | dependencia alta; media; **no** |
| eBay Buy **Browse** `GET /buy/browse/v1/item_summary/search` | listings, keyword/categoría/GTIN/EPID, precio observado | `EBAY_US`; actual al request | application token; Sandbox usa datos mock; Production Buy restringida/aprobación; límites oficiales por aplicación; coste no confirmado | Buy API requirements + API License; revisar retención/uso derivado antes de producción | Corroboración comercial y competencia; listings ≠ ventas | alta; media; **no** (Sprint 41 bloqueado) |
| eBay Buy **Feed API** `GET /buy/feed/v1/file` | feeds curados de items/categorías | marketplaces soportados; archivos periódicos | no Sandbox; Production restringida, aprobación y contratos; cuota oficial por app; coste no confirmado | mismas restricciones Buy; revisar descarga, retención y redistribución | Cobertura por lote; no es demanda ni acceso inmediato | muy alta; alta; **no** |
| **Google Trends API Alpha** | interés de búsqueda por término, región/subregión; series consistentes | US; hasta hace 2 días; ventana móvil 5 años | solicitud/allowlist Alpha; cuotas y coste no confirmados | términos Alpha; retención/derivación no confirmadas | Excelente cambio/estacionalidad; interés ≠ conversión/ventas | alta mientras Alpha; media; **no** |
| Google Ads **KeywordPlanIdeaService.GenerateKeywordIdeas** | ideas, avg monthly searches, competencia publicitaria; keyword | geo US; histórico según request | Google Ads customer, OAuth, developer token y nivel de acceso permitido; production; coste de API no confirmado | políticas Google Ads; guardar solo lo permitido; versiones rotan ~anualmente | Expansión de semillas e interés de búsqueda; competencia Ads ≠ competencia comercial | media/alta; media; **no** |
| Google **Merchant API** Products/Reports | catálogo, inventario e insights de la cuenta Merchant propia | feed label US; cercano a tiempo real según recurso | Merchant Center + Cloud project + developer registration + OAuth/service account; no catálogo público; coste no confirmado | datos de cuenta propia y políticas Shopping; no autoriza explorar comercios ajenos | Útil después para catálogo propio; no sirve para discovery abierto | alta; media; **no** |
| **Etsy Open API v3** `findAllListingsActive`, taxonomía/listings | presencia de listings, atributos, precio, favorers cuando expuesto | marketplace Etsy; filtro US no equivale a demanda US; timestamps por listing | API key; OAuth para scopes privados; QPS/QPD por key visibles en headers; coste no confirmado | términos API; caching/retención deben validarse en aprobación de app | Nichos handmade/digital y presencia; listing/favorer ≠ venta | media; media; **no** |
| Walmart Marketplace **Item Search** `GET /v3/items/walmart/search` | catálogo publicado por keyword/UPC/GTIN/ASIN, precio y atributos según respuesta | `WM_MARKET: US`; estado publicado actual | seller/approved solution provider + access token; hasta 40 matches por keyword; throttling por guía; coste no confirmado | uso para workflows de seller; no asumir permiso para minería independiente | Identidad y presencia Walmart; solo publicados, no ventas | alta; media; **no** |
| Walmart Connect **Insights Top Search Trends** | ranking diario de keywords + 3 items, click/conversion share | Walmart.com/app US; diario después de 4pm PST | exclusivo Walmart Connect Partner Network; Sandbox y Production tras onboarding; cuota/coste no confirmados | partner terms; retención/derivación por acuerdo | Señal comercial fuerte y explícita, pero inaccesible hoy | muy alta; alta; **no** |
| Best Buy **Products/Categories API v1** | catálogo presente/histórico, categoría, precio, disponibilidad, reviews | BestBuy.com US; precio casi real-time | email + API key; production; límite asignado no publicado en página general; coste no confirmado | términos prohíben cache salvo temporal; enlaces expiran 7 días; restricciones media/movies | Buena semilla electrónica y precio/presencia; catálogo/reviews ≠ ventas | media; baja/media; **no** hasta acción humana |
| U.S. Census **MRTS/MARTS** (`timeseries/eits/mrts`, `marts`) | ventas/inventario retail por categoría NAICS | US nacional; mensual | API HTTPS; las consultas actuales requieren key según guía; cuota/coste no confirmados | datos públicos; conservar fuente/metodología y revisar términos del dataset | Macro/category trend; no producto, keyword, canal ni conversión | baja; baja; **no** sin key para consultas actuales |
| U.S. Census **International Trade** (`timeseries/intltrade/imports/hs`) | valor/cantidad de importación por HS y país/puerto | US; mensual | API key requerida; cuota/coste no confirmados | datos públicos; atribución/metodología; clasificación HS puede cambiar | supply/category activity; importación ≠ demanda o margen | baja; media por mapeo HS; **no** sin key |
| **BLS Public Data API v2** | CPI/PPI/CES/Consumer Expenditure series por categoría | US; mensual/trimestral/anual según serie | GET sin registro: ventana/volumen limitado; key amplía límites; coste no confirmado | datos públicos; citar series/revisiones | inflación, empleo y gasto macro; no producto ni marketplace | baja; baja; **sí**, alcance limitado |
| **BEA Data API** NIPA/Regional `SAPCE*` | PCE por tipo de producto/estado, ingreso/GDP | US/estado; trimestral/anual según tabla | API key/registro oficial; cuota/coste no confirmado | estadísticas públicas; conservar tabla, unidad y revisión | contexto macro de consumo; no intención ni venta de producto | baja; baja; **no** sin key |
| **Data.gov CKAN API** `/api/3` | metadatos de datasets/licencias, no observaciones | US federal; metadata variable | público; autenticación/cuota/coste no confirmados | licencia pertenece al dataset enlazado | Descubrimiento de datasets, nunca señal comercial por sí mismo | baja; baja; **sí** como catálogo |
| Wikimedia **Pageviews API** `metrics/pageviews/per-article` | atención a artículo/tema, serie temporal | global; proyecto/idioma, no mercado US salvo proxy imperfecto; diaria | público con User-Agent; límites operativos documentados por Wikimedia; sin coste publicado | políticas Wikimedia/API; conservar proyecto, artículo y cobertura | Semilla indirecta ya disponible; pageviews ≠ demanda comercial | baja; baja; **sí** |
| Target / otros retailers sin portal oficial verificable | ninguna señal autorizada confirmada | no confirmado | no se verificó API pública oficial de catálogo/discovery | una página pública no autoriza automatización | No usar como fuente automatizada | alta; n/a; **no** |

## Documentación oficial primaria

- Amazon: [Creators API introduction](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction), [rates](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/concepts/api-rates).
- eBay: [Browse API](https://developer.ebay.com/api-docs/buy/static/api-browse.html), [Feed API](https://developer.ebay.com/api-docs/buy/api-feed.html).
- Google: [Trends API Alpha](https://developers.google.com/search/apis/trends), [Keyword Ideas](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-keyword-ideas), [Merchant API](https://developers.google.com/merchant/api/overview).
- Etsy: [Open API v3 reference](https://developers.etsy.com/documentation/reference), [rate limits](https://developers.etsy.com/documentation/essentials/rate-limits/).
- Walmart: [Marketplace Item Search](https://developer.walmart.com/global-marketplace/docs/item-search-for-the-walmart-catalog), [Top Search Trends](https://developer.walmart.com/advertising-partners-search/docs/overview-16).
- Best Buy: [Developer API](https://bestbuyapis.github.io/api-documentation/).
- Gobierno US: [Census economic indicators](https://www.census.gov/data/developers/data-sets/economic-indicators.html), [International Trade](https://www.census.gov/data/developers/data-sets/international-trade.html), [BLS API v2](https://www.bls.gov/developers/api_signature_v2.htm), [BEA API](https://apps.bea.gov/api/signup/), [Data.gov APIs](https://data.gov/developers/apis/).
- Wikimedia: [Wikimedia Analytics API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/).

## Fuentes descartadas para V1

- **Amazon Creators:** requisito circular de 10 ventas calificadas/30 días y uso
  orientado a Associates; no resuelve el caso pre-venta.
- **Google Trends Alpha y Walmart Connect Trends:** potencial alto, acceso
  allowlisted/partner y no disponible ahora.
- **Merchant API:** solo administra/consulta la cuenta Merchant autorizada; no es
  un catálogo universal de Shopping.
- **Etsy:** cobertura sectorial y necesidad de app key; queda como expansión.
- **Walmart Marketplace:** acceso condicionado a seller/solution provider; no se
  pedirá solo para discovery.
- **Target y páginas retail:** sin API pública oficial verificable; prohibido
  sustituirla por scraping.
- **Data.gov, BLS, BEA, Census y Wikimedia como fuente única:** sus señales son
  metadata, macro/category o atención y no satisfacen corroboración comercial.
- **datasets de terceros sin licencia, metodología, fecha o procedencia:** no
  ingresan al pipeline. Las opciones pagadas quedan `NO_DATA` hasta verificar
  oficialmente precio, licencia, retención y derecho de derivación.

## Respuestas de Source Selection V1

- **A.** Sí: contratos, semillas públicas y adaptadores futuros pueden
  construirse sin eBay. Hipótesis reales exigen una fuente comercial autorizada.
- **B.** Census MRTS/Trade + Wikimedia para semillas; Best Buy como primer
  adaptador comercial sujeto a aprobación humana; eBay luego como corroboración.
- **C.** Respectivamente: actividad macro/category/supply, atención indirecta,
  catálogo/precio/presencia, y listings/precio/presencia marketplace.
- **D.** Ventas/conversión, costes, supplier, restricciones, devoluciones,
  publicidad, sell-through y adecuación operativa siguen desconocidos.
- **E.** No usar Target/páginas retail vía scraping, Google Merchant como catálogo
  ajeno, ni Amazon Creators para evadir requisitos de Associates.
- **F.** Para datos reales V1 hace falta aprobación humana de una API key y sus
  términos (Best Buy o Census); no se solicita en este sprint. Sin esa acción se
  implementan contratos, fixtures sintéticos y pruebas, no evidencia real.
