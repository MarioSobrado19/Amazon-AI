# ADR-018 — GoalContextSnapshot inmutable

- **Estado:** aceptado
- **Fecha:** 2026-08-10

## Contexto

Presupuesto, tiempo, experiencia, región, capacidades, preferencias y
restricciones cambian. Una evaluación debe poder explicar qué contexto utilizó
sin afirmar que ese contexto sigue vigente.

## Decisión

Cada evaluación Goal-to-Business usará un `GoalContextSnapshot` inmutable,
fechado y versionado. Distinguirá datos declarados, estimaciones y supuestos, y
podrá conservar procedencia, confianza y vigencia cuando corresponda.

## Consecuencias

- Las evaluaciones son reproducibles y auditables.
- Actualizar el perfil genera un snapshot nuevo.
- Los datos ausentes permanecen ausentes; no se infieren silenciosamente.
- La retención y exposición del contexto estarán sujetas a privacidad y
  consentimiento.
