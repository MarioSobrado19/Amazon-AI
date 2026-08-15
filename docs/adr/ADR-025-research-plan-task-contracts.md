# ADR-025 — ResearchPlan y ResearchTask como contratos

- **Estado:** propuesto
- **Fecha:** 2026-08-14

## Contexto

Oriva necesita representar trabajo pendiente sin introducir colas o persistencia.

## Decisión

ResearchPlan será un snapshot inmutable de planificación y ResearchTask una
unidad semántica, explicable y trazable. Ninguno será workflow ni evidencia.

## Consecuencias

La planificación puede probarse en memoria y ejecutarse posteriormente mediante
infraestructura sustituible.
