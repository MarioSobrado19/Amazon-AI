# ADR-014 — Vigencia por tipo de información externa

- **Estado:** aceptado
- **Fecha:** 2026-08-08

## Contexto

Tarifas, políticas, restricciones, disponibilidad, requisitos y señales
comerciales cambian con ritmos distintos. Una expiración universal sería
arbitraria y podría aceptar información vieja o rechazar evidencia útil.

## Decisión

No existirá una ventana universal de expiración. Cada tipo de información tendrá
una política de freshness versionada que considere fuente, región, fecha de
consulta, vigencia declarada, volatilidad, confianza y estado de verificación.

Las políticas concretas se definirán antes de integrar cada fuente. La ausencia
de una política válida impedirá presentar una condición como vigente.

## Consecuencias

- Diferentes evidencias pueden vencer en momentos distintos.
- Marketplace Engine debe reportar estado de vigencia y contradicciones.
- Cambiar una política de freshness no reescribe evaluaciones históricas.
- Cada integración necesita monitoreo y pruebas de caducidad propias.
