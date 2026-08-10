# ADR-017 — Relación entre BusinessPath y OpportunityScenario

- **Estado:** aceptado
- **Fecha:** 2026-08-10

## Contexto

`OpportunityScenario` ya representa una evaluación concreta bajo marketplace,
modelo operativo, proveedor, costos, condiciones y supuestos. Copiar ese
contexto dentro de una ruta amplia produciría divergencias y dobles fuentes de
verdad.

## Decisión

`BusinessPath` representará la ruta amplia desde un objetivo y referenciará una
o varias `OpportunityScenario`. No duplicará el contexto interno de los
escenarios ni mutará sus oportunidades.

## Consecuencias

- Una ruta puede comparar alternativas operativas verificables.
- Los escenarios conservan identidad e historial independientes.
- Los cambios de una ruta no reescriben resultados históricos.
- La trazabilidad recorre referencias explícitas en vez de copias.
