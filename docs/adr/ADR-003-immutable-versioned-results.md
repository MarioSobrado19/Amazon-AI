# ADR-003 — Resultados inmutables y versionados

- **Estado:** aceptado
- **Fecha:** 2026-08-06

## Contexto

Las fórmulas, reglas y datos cambian. Recalcular silenciosamente un resultado
histórico destruiría la trazabilidad de decisiones anteriores.

## Decisión

Cada Resultado será inmutable e indicará fecha, contexto, naturaleza de la
información, fuente y versiones de contrato, reglas y motor. Un nuevo cálculo
creará un Resultado nuevo.

## Consecuencias

- Las decisiones históricas pueden reconstruirse.
- Comparar versiones requiere referencias explícitas.
- Aumenta el almacenamiento, pero mejora auditoría y explicabilidad.
- Recomendaciones nuevas no borran las anteriores.

