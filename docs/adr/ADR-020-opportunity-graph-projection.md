# ADR-020 — Opportunity Graph como proyección no canónica

- **Estado:** aceptado
- **Fecha:** 2026-08-10

## Contexto

Oriva necesita recorrer relaciones entre objetivos, proyectos, oportunidades,
escenarios, evidencia, recomendaciones y resultados. Esa necesidad conceptual
no justifica imponer una base de datos de grafos ni duplicar el modelo oficial.

## Decisión

Opportunity Graph será una proyección reconstruible o read model. Las entidades,
resultados, snapshots e historial oficiales seguirán siendo la fuente canónica.
Los contratos serán neutrales respecto de persistencia y motor de consulta.

## Consecuencias

- El grafo puede materializarse en memoria, documentos, SQL o tecnología de
  grafos sin cambiar el Core.
- Una proyección puede regenerarse desde fuentes canónicas.
- Los nodos y relaciones referencian identidades oficiales; no las sustituyen.
- La autorización debe aplicarse también a recorridos y vistas derivadas.
