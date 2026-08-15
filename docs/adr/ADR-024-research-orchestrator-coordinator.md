# ADR-024 — Research Orchestrator coordina, no investiga

- **Estado:** propuesto
- **Fecha:** 2026-08-14

## Contexto

Coordinar necesidades no debe mezclar reglas de fuentes, búsqueda o evaluación.

## Decisión

Research Orchestrator será un servicio de Application que planifica y consolida.
No consulta fuentes, calcula conocimiento, recomienda negocios ni toma decisiones.

## Consecuencias

Las capacidades especializadas conservan sus reglas y pueden evolucionar sin
contaminar el coordinador. Los fallos se representan como estado de trabajo.
