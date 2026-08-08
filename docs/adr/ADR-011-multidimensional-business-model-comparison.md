# ADR-011 — Comparación multidimensional sin score único inicial

- **Estado:** aceptado
- **Fecha:** 2026-08-08

## Contexto

Un único puntaje podría ocultar diferencias importantes entre capital, tiempo,
experiencia, logística y riesgo, especialmente con evidencia incompleta.

## Decisión

La primera comparación de BusinessModel será multidimensional y explicable.
Incluirá como mínimo capital, tiempo, experiencia, carga operativa, logística,
riesgo, requisitos, restricciones, escalabilidad y contexto del usuario.

No se implementará un Business Model Score en esta etapa. Cualquier propuesta
futura requerirá ADR propio, pesos auditables, versionado y explicación completa.

## Consecuencias

- El usuario ve compensaciones en lugar de una clasificación opaca.
- Presupuesto no puede decidir por sí solo.
- La UI deberá presentar varias dimensiones de manera comprensible.
- Ordenar automáticamente modelos requerirá una decisión arquitectónica futura.
