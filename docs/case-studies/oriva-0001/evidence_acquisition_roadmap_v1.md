# Roadmap de adquisición de evidencia v1

> **INTERNAL / CONFIDENTIAL — ORIVA.** Priorización para revisión humana. No
> autoriza conexiones, credenciales, pagos, contacto, gasto ni acción comercial.

## Método de prioridad

No se usa score. El orden sigue dependencias y valor informativo: primero se
reduce el espacio de búsqueda con evidencia capaz de identificar rutas reales;
después se comprueban demanda y competencia; luego viabilidad de suministro y
restricciones; finalmente se completan costes, economía y capacidad. Una ruta
puede volver a una etapa anterior cuando nueva evidencia cambie su identidad.

## Prioridad 0 — contexto operativo humano

- **Pregunta:** ¿qué tiempo semanal, almacenamiento, trabajo físico, habilidades
  y complejidad operativa están disponibles?
- **Bloqueo:** bloquea filtros prácticos, pero una preferencia no causa STOP ni
  invalida silenciosamente una ruta.
- **Evidencia mínima:** declaración humana fechada, separando preferencias de
  restricciones duras.
- **Fuente/acceso:** humano responsable; sin API, credenciales ni pago.
- **Freshness/alcance:** confirmar al iniciar y ante un cambio material; US y
  cualquier marketplace.
- **Legal/TOS/coste:** bajo; minimizar PII. Coste externo: ninguno identificado.
- **Consumidor/decisión:** GoalContextSnapshot; habilita criterios de búsqueda y
  revisión sin crear todavía un candidato financiable.

## Prioridad 1 — Opportunity/Product Discovery

- **Pregunta:** ¿qué productos o rutas observables merecen convertirse en
  hipótesis investigables en US sin preseleccionar marketplace?
- **Bloqueo:** bloquea la identidad del candidato; sin ella, demanda, proveedor,
  fees y regulación no pueden consultarse con precisión.
- **Evidencia mínima:** una fuente legítima que produzca identidad resoluble
  (producto/categoría/consulta), mercado, fecha, procedencia y limitaciones;
  preferiblemente señales de más de un canal o una fuente oficial con cobertura
  declarada. La salida son hipótesis, no candidatos de inversión.
- **Fuentes posibles:** catálogos y tendencias publicados por marketplaces;
  datos abiertos oficiales de comercio; fuentes comerciales autorizadas; y
  observación manual permitida y registrada. Deben revisarse alcance y términos
  antes de elegir una fuente concreta.
- **Acceso/coste:** puede requerir API, cuenta, credenciales, licencia o pago
  según la fuente; todo requiere aprobación previa. Coste: no verificado.
- **Freshness/alcance:** captura fechada; semanal o mensual para señales de
  cambio rápido, validada de nuevo antes de decidir. US, sin marketplace fijo.
- **Legal/TOS:** riesgo medio; evitar scraping prohibido, reidentificación,
  redistribución no autorizada y claims que excedan el dato.
- **Consumidor/decisión:** Goal-to-Business, Research Orchestrator y Opportunity
  Graph; habilita una lista pequeña de hipótesis nominadas para investigación,
  no inversión ni promoción automática a BusinessPath.

## Prioridad 2 — Commercial Demand real

- **Pregunta:** ¿existen transacciones o intención comercial vigente para la
  identidad exacta, en US y en los canales candidatos?
- **Bloqueo:** bloquea evaluación de ventas y escalabilidad; puede ejecutarse en
  paralelo con competencia una vez exista identidad.
- **Evidencia mínima:** señal comercial atribuible a producto/consulta, ventana,
  región y canal, con unidad y cobertura conocidas; corroboración independiente
  cuando la fuente solo sea proxy. Wikimedia no satisface este mínimo.
- **Fuentes posibles:** datos oficiales o APIs autorizadas de marketplaces,
  informes first-party con metodología, datos autorizados de tendencias de
  compra/búsqueda y observación manual permitida.
- **Acceso/coste:** API/cuenta/licencia posiblemente necesarias; aprobación
  previa. Coste: no verificado.
- **Freshness/alcance:** idealmente últimos 30–90 días y estacionalidad histórica
  cuando sea material; US y marketplace identificado.
- **Legal/TOS:** riesgo medio/alto según proveedor; respetar límites de uso,
  retención y redistribución.
- **Consumidor/decisión:** Demand Research, ResearchFinding y Opportunity Graph;
  habilita continuar, mantener HOLD o reducir prioridad de una hipótesis.

## Prioridad 2 — Commercial Competition real

- **Pregunta:** ¿qué oferta, precios, concentración, diferenciación y condiciones
  observables existen para la identidad exacta en cada canal?
- **Bloqueo:** bloquea interpretación de demanda y precio realizable; corre en
  paralelo con demanda.
- **Evidencia mínima:** resultados reales fechados, consulta/categoría exacta,
  moneda, región, marketplace, paginación/cobertura y limitaciones; Sandbox y
  fixtures permanecen separados.
- **Fuentes posibles:** APIs oficiales de marketplace y observación manual
  permitida. eBay Browse queda pendiente exclusivamente de aprobación y revisión
  de Sprint 41; este roadmap no intenta conectarlo.
- **Acceso/coste:** normalmente cuenta/API/credenciales y aprobación; posibles
  cuotas. Coste: no verificado.
- **Freshness/alcance:** captura reciente, normalmente días o semanas según
  volatilidad; US y marketplace específico.
- **Legal/TOS:** riesgo medio; límites de API, almacenamiento, uso derivado y
  presentación deben revisarse.
- **Consumidor/decisión:** Competition Research y Opportunity Graph; habilita
  evaluar saturación y posicionamiento, nunca inferir ventas sin evidencia.

## Prioridad 3 — Supplier, MOQ y lead time

- **Pregunta:** ¿existe suministro legítimo para el artículo exacto, a qué coste,
  MOQ, calidad, disponibilidad, términos y plazo?
- **Bloqueo:** bloquea landed cost, capital de trabajo y factibilidad. No debe
  preceder una identidad con demanda suficiente, para evitar contacto y trabajo
  dispersos.
- **Evidencia mínima:** oferta o documento autorizado, fechado y atribuible, con
  SKU/especificación, moneda, incoterm, MOQ, tiers, lead time, vigencia y exclusiones.
- **Fuentes posibles:** portales oficiales/autorizados, distribuidores y, solo
  tras aprobación separada, cotizaciones directas.
- **Acceso/coste:** puede requerir cuenta, API, pago o contacto; todos prohibidos
  ahora sin nueva aprobación. Coste de datos/sourcing: no verificado.
- **Freshness/alcance:** validar dentro de la vigencia de oferta y antes de cada
  decisión; origen y destino US explícitos.
- **Legal/TOS:** riesgo medio/alto; autenticidad, marcas, seguridad, privacidad,
  términos de plataforma y restricciones de exportación/importación.
- **Consumidor/decisión:** Supplier Research y EvidenceRecord; habilita evaluar
  factibilidad y preparar landed cost, no comprar.

## Prioridad 3 — Restrictions y regulation

- **Pregunta:** ¿qué requisitos legales, regulatorios, de seguridad, marca,
  importación y plataforma aplican al candidato exacto?
- **Bloqueo:** bloquea GO cuando afecte legalidad o seguridad y puede justificar
  STOP con evidencia material; debe empezar temprano para categorías sensibles.
- **Evidencia mínima:** texto oficial vigente y aplicable, jurisdicción, categoría,
  fecha efectiva y obligación concreta; revisión experta si la interpretación
  excede una comprobación documental.
- **Fuentes posibles:** reguladores federales/estatales de US, aduanas, registros
  oficiales y políticas del marketplace.
- **Acceso/coste:** normalmente público; asesoría o bases especializadas requieren
  aprobación. Coste: no verificado.
- **Freshness/alcance:** comprobar al investigar y antes de cualquier acción;
  US, estado aplicable y marketplace.
- **Legal/TOS:** alto impacto; no presentar el análisis como asesoría legal.
- **Consumidor/decisión:** Policy/Restriction Research y Decision Engine; habilita
  GO/HOLD/STOP explicable por criterio.

## Prioridad 4 — Marketplace fees y fulfillment completos

- **Pregunta:** ¿qué fees, almacenamiento, fulfillment, pagos, devoluciones y
  condiciones corresponden a categoría, dimensiones, precio y modelo exactos?
- **Bloqueo:** bloquea contribución unitaria, pero depende de producto, canal,
  modelo, dimensiones y precio; investigarlo genéricamente antes produce tablas
  extensas con poco valor decisional.
- **Evidencia mínima:** schedules/calculadores oficiales vigentes con categoría,
  tier, dimensiones/peso, moneda, región, fecha y supuestos trazables.
- **Fuentes posibles:** páginas, tablas, calculadores y APIs oficiales del
  marketplace y operador logístico.
- **Acceso/coste:** parte pública; calculadores/API pueden requerir cuenta o
  credenciales. Coste de acceso: no verificado.
- **Freshness/alcance:** vigente a la fecha y reconfirmado antes de decisión; US
  y marketplace/modelo concretos.
- **Legal/TOS:** bajo/medio; respetar términos y no automatizar interfaces sin
  autorización.
- **Consumidor/decisión:** Marketplace Conditions, Business Model Engine y
  Reverse Economics; habilita cálculo parcial de contribución.

## Prioridad 4 — Landed costs

- **Pregunta:** ¿cuál es el coste unitario puesto en el punto de recepción para
  el origen, cantidad, dimensiones, transporte, arancel y seguro aplicables?
- **Bloqueo:** bloquea contribución y capital; depende de producto y suministro.
- **Evidencia mínima:** desglose fechado de producto, flete, seguro, arancel,
  brokerage, recepción y demás componentes materiales; cantidad e incoterm.
- **Fuentes posibles:** oferta autorizada, tarifas oficiales de aduanas y
  transportista/logística autorizados.
- **Acceso/coste:** puede requerir cotización/cuenta/contacto y aprobación. Coste
  de acceso: no verificado.
- **Freshness/alcance:** dentro de vigencia de cotización; ruta hacia US.
- **Legal/TOS:** medio/alto; clasificación arancelaria y obligaciones de importador
  requieren validación competente.
- **Consumidor/decisión:** Supplier/Landed Cost Research y Reverse Economics;
  habilita contribución y desembolso de reposición.

## Prioridad 5 — Returns, advertising y sell-through

- **Pregunta:** ¿qué devoluciones/merma, publicidad y velocidad de venta son
  aplicables y sostenibles para el candidato?
- **Bloqueo:** bloquean un escenario económico cuando son materiales; antes de
  disponer de identidad/demanda/precio solo pueden ser ASSUMPTION explícita.
- **Evidencia mínima:** tasas atribuibles a categoría/canal/periodo o escenarios
  separados con rango y fuente; nunca mezclar estimación con resultado real.
- **Fuentes posibles:** políticas y reportes oficiales, datos autorizados de
  categoría/cuenta cuando existan, benchmarks con metodología declarada.
- **Acceso/coste:** puede requerir cuenta, API, licencia o datos operativos;
  aprobación previa. Coste: no verificado.
- **Freshness/alcance:** 30–90 días más estacionalidad si aplica; US y canal.
- **Legal/TOS:** medio; privacidad, uso de datos de cuenta y redistribución.
- **Consumidor/decisión:** Demand Research y Reverse Economics; habilita
  sensibilidad y capacidad de rotación.

## Prioridad 6 — Working capital y capacidad operativa

- **Pregunta:** ¿qué efectivo pico, inventario, reposición, horas, espacio y
  soporte exige cada escenario de primera venta, break-even, USD 1k, 3k y 5k+?
- **Bloqueo:** bloquea GO hacia validación y escalabilidad, pero es cálculo
  derivado de demanda, contribución, MOQ, lead time y operación.
- **Evidencia mínima:** inputs previos trazables, fórmula, calendario de caja,
  capacidad declarada y sensibilidad; `NOT CALCULABLE` si falta un input material.
- **Fuentes posibles:** ledger del caso, términos de payout/fulfillment oficiales,
  evidencia de proveedor y declaración humana de capacidad.
- **Acceso/coste:** sin conexión nueva si los inputs ya existen. Coste externo:
  ninguno identificado para el cálculo documental.
- **Freshness/alcance:** recalcular con cada cambio material; US, canal y modelo.
- **Legal/TOS:** bajo; proteger información financiera y operativa interna.
- **Consumidor/decisión:** Reverse Economics y Decision Engine; habilita comparar
  escenarios contra USD 750 y límites humanos, sin convertirlos en targets.

## Elección del siguiente frente después de eBay

**Recomendación: D. Opportunity/Product Discovery.** Es el cuello de botella
anterior a los otros tres frentes. El caso no tiene producto, categoría,
marketplace ni modelo; por eso Demand Research no tiene una entidad exacta que
consultar, Supplier Research no tiene un artículo que cotizar, y fees +
fulfillment no tienen categoría/dimensiones/modelo. Discovery debe producir una
lista pequeña de hipótesis con procedencia y cobertura; no candidatos de
inversión. Después, Demand Research y Competition Research deben ejecutarse en
paralelo sobre cada identidad, antes de Supplier Research y fees completos.

## Condición concreta para salir del HOLD de adquisición hacia investigación de candidatos

El caso puede pasar exactamente a **`HOLD/RESEARCHING — hypotheses identified`**
—no a inversión ni gasto— cuando existan: (1) contexto operativo humano
suficiente, con preferencias separadas de restricciones; (2) señales US recientes
de una fuente macro/category oficial; (3) identidades reales resueltas mediante
una API de catálogo autorizada y revisada en TOS; (4) un segundo tipo de señal no
redundante por identidad; y (5) una salida fechada, revisada por humano, de 3–10
hipótesis con procedencia, cobertura, limitaciones, contradicciones y unknowns,
sin fixtures ni estimaciones presentadas como realidad. Cada hipótesis debe crear
ResearchNeeds explícitos para demanda, competencia, suministro, restricciones y
costes. Hasta entonces, el estado sigue siendo `HOLD — evidence acquisition`.
Después de la transición, `current_candidates` permanece vacío y capital
autorizado, gastado y arriesgado continúa en USD 0: una hipótesis no es
`Opportunity`, `CandidateBusinessPath`, autorización ni recomendación.
