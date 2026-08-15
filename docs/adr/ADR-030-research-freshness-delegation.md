# ADR-030 — Freshness delegada por tipo de información

- **Estado:** propuesto
- **Fecha:** 2026-08-14

## Decisión

El Orchestrator consume freshness. Capabilities, adaptadores o configuración
versionada definen políticas por tipo de información; no existe TTL universal.

## Consecuencias

Precio, tarifas, políticas, demanda y proveedor pueden tener vigencias distintas
sin reglas temporales ocultas dentro del coordinador.
