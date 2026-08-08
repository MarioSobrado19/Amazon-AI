# ADR-013 — IA como explicador, no fuente de verdad externa

- **Estado:** aceptado
- **Fecha:** 2026-08-08

## Contexto

Una IA puede adaptar explicaciones y mantener una conversación, pero puede
inventar o desactualizar tarifas, políticas, restricciones y requisitos.

## Decisión

La IA podrá explicar, comparar y guiar. No será fuente de verdad de condiciones
externas críticas. Esos datos procederán de fuentes verificables, adaptadores y
MarketplaceConditionSnapshot versionados.

Toda explicación deberá distinguir hechos recuperados, resultados de motores,
supuestos y texto generado. Si falta evidencia vigente, deberá decirlo.

## Consecuencias

- La IA no eleva confianza ni crea políticas.
- Las respuestas deben conservar citas y trazabilidad.
- La ausencia de evidencia limita la respuesta en lugar de estimular una
  invención.
- La experiencia conversacional puede evolucionar sin redefinir el Core.
