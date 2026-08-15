# ADR-026 — Identidad semántica separada de ejecución

- **Estado:** propuesto
- **Fecha:** 2026-08-14

## Decisión

Plan y tarea usan IDs deterministas por pregunta, sujeto y contexto relevante.
Cada intento real usa un execution ID opaco nuevo. Timestamps de planificación
no alteran identidad semántica.

## Consecuencias

Se evitan duplicados sin borrar actualizaciones o intentos históricos legítimos.
