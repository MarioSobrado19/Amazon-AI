# ADR-029 — Fallos parciales conservan resultados válidos

- **Estado:** propuesto
- **Fecha:** 2026-08-14

## Decisión

El estado del plan se agrega por tarea. Un fallo no elimina EvidenceRecord de
otras tareas ni convierte necesariamente el plan en fallido.

## Consecuencias

`partial`, `blocked` y `failed` permanecen semánticamente distintos; retryable
describe el fallo técnico, no la oportunidad.
