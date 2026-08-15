# ADR-027 — Reutilización estricta de evidencia

- **Estado:** propuesto
- **Fecha:** 2026-08-14

## Decisión

Solo evidencia aplicable por sujeto, pregunta, región, marketplace, periodo,
tipo, verificación y freshness puede cubrir una tarea. Evidencia vencida,
parcial o conflictiva permanece visible pero no cierra requisitos más fuertes.

## Consecuencias

Se reducen consultas redundantes sin convertir coincidencias superficiales en
hechos ni borrar historial.
