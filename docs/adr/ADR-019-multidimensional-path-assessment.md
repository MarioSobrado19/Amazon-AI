# ADR-019 — PathAssessment multidimensional

- **Estado:** aceptado
- **Fecha:** 2026-08-10

## Contexto

La compatibilidad de una ruta depende de capital, tiempo, experiencia, carga
operativa, logística, riesgo, requisitos, restricciones, escalabilidad y
evidencia. Un puntaje único ocultaría compensaciones importantes.

## Decisión

`PathAssessment` será multidimensional, explicable e inmutable. Cada dimensión
conservará evidencia favorable, riesgos, restricciones, datos faltantes y la
parte del contexto que influyó. No se implementará un score único.

La suficiencia de evidencia se definirá mediante políticas versionadas por
etapa y capacidad, no mediante un conteo universal.

## Consecuencias

- El usuario puede entender por qué una ruta encaja o no.
- Una restricción fuerte no queda escondida por fortalezas menores.
- Caminos incompletos pueden representarse sin presentarlos como validados.
- Cualquier score futuro exigirá ADR, pesos auditables y explicación completa.
