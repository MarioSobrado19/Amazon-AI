# ADR-028 — Dependencias de investigación como DAG

- **Estado:** propuesto
- **Fecha:** 2026-08-14

## Decisión

Las dependencias forman un DAG validado. Se rechazan referencias inexistentes,
self-dependencies y ciclos. Niveles topológicos expresan paralelismo potencial.

## Consecuencias

El diseño admite concurrencia futura sin imponer ahora un workflow engine.
