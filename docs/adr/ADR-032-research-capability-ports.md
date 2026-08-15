# ADR-032 — Extensibilidad mediante ResearchCapability ports

- **Estado:** propuesto
- **Fecha:** 2026-08-14

## Decisión

Capacidades genéricas implementan puertos versionados y declaran cobertura,
inputs, outputs, autorización, coste y limitaciones. Integraciones concretas
quedan en adaptadores anticorrupción fuera del Core.

## Consecuencias

Marketplace, Demand, Competition, Supplier y capacidades futuras pueden añadirse
sin modificar el núcleo del Orchestrator ni introducir marcas en el dominio.
