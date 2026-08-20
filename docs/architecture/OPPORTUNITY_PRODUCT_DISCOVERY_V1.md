# Opportunity/Product Discovery V1

> **INTERNAL / CONFIDENTIAL — ORIVA.** Diseño para revisión humana. Discovery
> propone qué investigar; nunca declara qué comprar, vender o financiar.

## Límite de la capacidad

```text
Objective + GoalContextSnapshot
  -> DiscoverySeed + DiscoverySignal/EvidenceRecord
  -> OpportunityHypothesis
  -> ResearchNeed[]
  -> Research Orchestrator
  -> Demand + Competition + Supplier + Costs + Restrictions
  -> evaluación y decisión humana posteriores
```

Discovery no crea `Opportunity`, `OpportunityScenario`, `CandidateBusinessPath`,
`BusinessPath`, `Recommendation` ni `Decision`. Esos conceptos existentes no se
duplican. Una hipótesis es un contrato efímero, reconstruible y anterior a
`Opportunity`; solo puede promoverse mediante un paso explícito posterior.

## Taxonomía de señales

| Tipo | Afirma | No afirma |
|---|---|---|
| `catalog_presence` | identidad presente en catálogo | ventas u oportunidad |
| `attention` | atención al tema en el canal medido | demanda comercial |
| `search_interest` | interés relativo/volumen de búsqueda según fuente | conversión |
| `commercial_listing_presence` | listings observables en marketplace | ventas ni saturación |
| `price_observation` | precio anunciado en fecha/canal | precio realizado o margen |
| `category_activity` | cambio agregado de ventas/inventario/catálogo | resultado de producto |
| `marketplace_presence` | identidad resoluble en un canal | viabilidad para Oriva |
| `supply_signal` | flujo, disponibilidad o catálogo de suministro | proveedor elegible o landed cost |
| `macro_consumer_signal` | consumo/precio agregado | intención de compra individual |
| `trend_change` | cambio medido dentro de una serie comparable | persistencia futura |

Invariantes obligatorias: Pageviews ≠ demanda; listings ≠ ventas; search
interest ≠ conversiones; catálogo ≠ oportunidad; precio observado ≠ margen.
La semántica original de fuente se conserva y nunca se normaliza todo a
`ResearchCategory.DEMAND`.

## Contratos mínimos implementados

Se implementan en Application, no en Domain, para validar el concepto
provisional sin contaminar el núcleo permanente.

### `DiscoverySignal`

```text
signal_id                 UUIDv5(tipo + identidad + fuente + referencia + fecha + método + valor)
signal_type               enum de la taxonomía anterior
subject_identity          concepto/categoría/keyword/GTIN/ASIN/UPC cuando exista
region                    Region | null
marketplace_id            str | null
observed_at/retrieved_at  datetime aware
freshness                 FreshnessStatus
verification_status       VerificationStatus
source/source_reference   procedencia oficial, sin secretos
evidence_id               referencia a EvidenceRecord cuando ya sea evidencia
limitations               tuple[str]
method_version            str
```

Una señal que todavía no tenga sujeto estable es `DiscoverySeed`; no se fuerza
dentro de `EvidenceRecord`, cuyo `subject_id` exige identidad previa.

### `OpportunityHypothesis`

```text
hypothesis_id             UUIDv5(tipo + identidad normalizada + región + método)
identity_kind             product | concept | category | keyword
identity_value            texto/identificador normalizado, nunca inventado
region                    Region
potential_marketplaces    tuple[str] (posibles, no ganadores)
originating_signal_ids    tuple[str] (mínimo dos tipos no redundantes)
evidence_ids              tuple[str]
source_provenance         tuple[str]
observed_at               datetime aware (última observación material)
freshness                 FreshnessStatus
verification_status       VerificationStatus
why_surfaced              tuple[str] de reglas satisfechas
limitations               tuple[str]
unknowns                  tuple[str]
contradictions            tuple[str]
research_needs            tuple[ResearchNeed]
method_version            str
state                     surfaced | research_ready | stale | contradicted | excluded
```

Campos prohibidos: `success_probability`, `global_score`, `hidden_weight`,
`guaranteed_margin`, `winner`, `recommendation_to_buy`, demanda inventada y
cualquier autorización financiera.

## Generación explicable, deduplicación y límites

1. Ingerir semillas allowlisted y conservar la semántica de cada fuente.
2. Resolver identidad con identificadores fuertes; si solo hay texto, normalizar
   Unicode/case/espacios y conservar el original.
3. Agrupar equivalencias únicamente mediante reglas versionadas y explicables.
   Coincidencia semántica probabilística solo propone un grupo para revisión; no
   fusiona identidades automáticamente.
4. Aplicar restricciones duras declaradas. Las preferencias solo añaden notas o
   categorías de investigación; nunca excluyen silenciosamente.
5. Exigir dos tipos de señal no redundantes y al menos una señal de presencia
   comercial/catalogada autorizada para `research_ready`. Una fuente repetida no
   cuenta como corroboración independiente.
6. Emitir `why_surfaced` con reglas legibles y `why_excluded` en el registro de
   exclusión. No existe suma ponderada.
7. Limitar cada corrida a 3–10 hipótesis, máximo configurable de semillas por
   categoría y cupos de diversidad explícitos por categoría/forma operativa.
8. Resolver prioridad de investigación por dependencias: identidad y
   restricciones críticas; demanda/competencia; supplier/costes. Los empates son
   deterministas por `hypothesis_id`, no por score oculto.

## Goal-to-Business

`Objective` define el propósito y `GoalContextSnapshot` aporta hechos fechados.
Para Caso #0001:

- región US es restricción de cobertura;
- USD 750 es techo futuro para formular ResearchNeeds de MOQ/working capital,
  no una señal de atractivo;
- capital autorizado USD 0 impide cualquier acción pagada o comercial;
- 90 días orienta freshness y preguntas de lead time, no predice primera venta;
- menor trabajo físico/complejidad logística es preferencia y genera diversidad
  y preguntas operativas, no exclusión automática;
- escalabilidad genera necesidades de capacidad/working capital; USD 5k+ sigue
  siendo escenario de reverse economics, nunca promesa;
- experiencia/capacidades ausentes permanecen `unknown`, no se imputan.

La coordinación versionada `Objective -> snapshot factual -> señales tipadas ->
hipótesis explicables -> DAG de ResearchNeeds`, manteniendo separados restricciones,
preferencias, evidencia y decisiones, es **IP review candidate**. También lo son
la identidad determinista reconstruible, las explicaciones simétricas de
inclusión/exclusión y la promoción por suficiencia semántica sin score. Esta
clasificación no afirma novedad jurídica ni patentabilidad.

## Arquitectura incremental

- `application.discovery_models`: contratos efímeros implementados; Domain
  queda intacto hasta validar su estabilidad.
- `OpportunityDiscoveryService`: coordina normalización, reglas, diversidad,
  límites, deduplicación y creación de ResearchNeeds; no hace red ni decide.
- `application.ports.discovery_source.DiscoverySource`: puerto genérico que
  recibe una solicitud fechada y devuelve señales tipadas o un estado explícito.
- adapters futuros separados por capacidad/señal, no por proveedor.
- adapters futuros: Census, Wikimedia existente (adaptado sin renombrarlo como
  demanda), Best Buy y después eBay/Walmart bajo autorización separada.
- mapper explícito crea `EvidenceRecord` solo cuando existe sujeto estable;
  conserva source reference, observed/retrieved, region, marketplace, freshness,
  verification y limitations.
- freshness delegada por tipo/fuente; evidencia stale no se borra y no inicia
  nuevas hipótesis sin refresh.
- fallos parciales tipados: `NO_DATA` no es `TECHNICAL_FAILURE`; una fuente caída
  no elimina señales válidas ni rebaja silenciosamente el umbral.

La primera suite cubre identidad determinista, deduplicación, prohibición de
score/ranking, dos señales no redundantes, contradicciones, freshness, fallos
parciales, asociación con `EvidenceRecord`, inmutabilidad, serialización y el
contexto del Caso #0001. Los fixtures son `SYNTHETIC / NOT REAL EVIDENCE` y no
pueden activar `hypotheses_identified`; los smoke checks reales siguen sujetos a
fuente legítima, autorización y credenciales cuando correspondan.

## Caso #0001 y condición exacta de transición

No se nombran productos ficticios. Para obtener las primeras 3–10 hipótesis
reales hacen falta:

1. completar/confirmar el `GoalContextSnapshot` con horas, almacenamiento,
   logística, experiencia y distinguir preferencias de restricciones;
2. capturar observaciones US recientes de una fuente macro/category oficial;
3. resolver de esas observaciones identidades reales mediante una API de catálogo
   autorizada, con procedencia, cobertura y timestamps;
4. corroborar cada identidad con un segundo tipo de señal no redundante;
5. mapear EvidenceRecords y crear ResearchNeeds bloqueantes para Demand,
   Competition, Supplier, Costs y Restrictions;
6. obtener revisión humana del paquete de 3–10, sin promoverlo a Opportunity.

Solo entonces el caso pasa exactamente a **`HOLD/RESEARCHING — hypotheses
identified`**. `current_candidates` continúa vacío, capital autorizado/gastado/
arriesgado sigue USD 0 y no se habilita compra, listing, matching, BusinessPath
ni decisión automática.

## Riesgos y controles

| Riesgo | Control obligatorio |
|---|---|
| proxy convertido en demanda | tipo de señal inmutable + limitación visible |
| TOS/licencia | allowlist por fuente/operación; revisión humana antes de credencial |
| ranking opaco | reglas versionadas, `why_surfaced`/`why_excluded`, sin score |
| explosión/dominancia de categoría | topes y cupos de diversidad declarados |
| identidad falsa | identificador fuerte o revisión humana; no auto-merge probabilístico |
| evidencia vieja | política por tipo, estado stale y refresh bloqueante |
| dependencia de proveedor | ports por señal, fallos parciales y provenance |
| filtrado injustificado por contexto | restricciones y preferencias separadas |
| fuga de IP | documentación técnica INTERNAL; marketing sin mecanismo novedoso |
