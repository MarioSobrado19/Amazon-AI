# Mapa de arquitectura y capacidades v1

## Encaje del caso

```text
Case package (documental, no entidad Domain)
→ Objective + GoalContextSnapshot
→ Goal-to-Business
→ CandidateBusinessPath(s)
→ acción humana explícita
→ BusinessPath
→ Research Foundation / ResearchAssessment
→ Research Orchestrator / ResearchPlan
→ ResearchCapabilities compatibles
→ EvidenceRecord / Finding / Conflict
→ Opportunity Graph
→ Decision Engine como recomendación explicable
→ decisión humana
```

No se instancia aún la cadena: faltan contexto material y una ruta candidata
legítima. Hacerlo hoy obligaría a inventar producto, marketplace o business
model. El paquete define el contexto que deberá mapearse a
`GoalContextSnapshot`; sus unknowns permanecen explícitos.

## Capacidades disponibles hoy desde main limpio

| Capability | Dimensión exacta | Uso legítimo hoy | Límite material |
| --- | --- | --- | --- |
| Amazon US Marketplace Conditions V1 | `marketplace` | Consultar las tarifas base públicas de planes Amazon US cuando exista un BusinessPath con `marketplace_id=amazon-us` | No incluye referral fees, FBA, almacenamiento, publicidad, impuestos, categoría, demanda ni competencia |
| Wikimedia Pageviews V1 | `demand` como señal indirecta de atención | Consultar vistas de un artículo exacto, sin región/marketplace, para un periodo histórico completo | No mide demanda comercial, intención, ventas, US ni marketplace; no resuelve entidades |
| Library of Congress probe | presencia documental neutral | Contexto experimental separado | No es ResearchCapability, no produce EvidenceRecord y permanece fuera de Competition Research |

## Bloqueos actuales

- identificación de oportunidades basada en mercado real;
- demanda comercial de US por candidato;
- competencia comercial real por marketplace;
- proveedor, MOQ, disponibilidad, lead time y cotización;
- landed cost;
- fees completos por categoría y fulfillment;
- restricciones/regulación específicas;
- devoluciones, publicidad y sell-through;
- capital de trabajo y capacidad operativa.

Sprint 41/eBay no forma parte de este worktree. Aunque su implementación local
existe en otro worktree, permanece pendiente de aprobación externa y revisión;
no se conecta ni se presenta como capability disponible.

## Conclusión operativa

Oriva puede planificar y representar faltantes hoy, y puede obtener dos señales
estrechas cuando una pregunta compatible esté definida. No puede evaluar una
oportunidad end-to-end ni generar candidatos legítimos de inversión con las
fuentes actuales. El resultado correcto es adquirir evidencia, no rellenar la
ausencia con productos populares o fixtures.
