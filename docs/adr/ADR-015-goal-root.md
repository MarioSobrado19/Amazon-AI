# ADR-015 — Objetivo como raíz de Goal-to-Business

- **Estado:** aceptado
- **Fecha:** 2026-08-10

## Contexto

Oriva ya reconoce `Objective` en su modelo oficial. Crear además
`BusinessGoal` duplicaría significado, identidad e historial sin aportar una
responsabilidad distinta.

## Decisión

`Objective` será la raíz conceptual del flujo Goal-to-Business. Su contexto
operativo se capturará por separado mediante `GoalContextSnapshot`, sin añadir
una entidad `BusinessGoal`.

## Consecuencias

- Se reutiliza el lenguaje oficial del dominio.
- Un objetivo puede evaluarse bajo varios contextos históricos.
- Cambiar recursos o restricciones no reescribe el objetivo.
- Cualquier especialización futura requerirá una responsabilidad distinta y un
  ADR propio.
