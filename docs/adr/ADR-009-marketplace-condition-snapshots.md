# ADR-009 — Snapshots versionados de condiciones de marketplace

- **Estado:** aceptado
- **Fecha:** 2026-08-08

## Contexto

Tarifas, políticas, restricciones, requisitos y disponibilidad cambian. Guardar
estos valores como atributos permanentes produciría evaluaciones no auditables.

## Decisión

`MarketplaceConditionSnapshot` representará una captura inmutable, versionada,
fechada y regionalizada de condiciones externas. Todo snapshot conservará
fuente, fecha de consulta, vigencia, versión, confianza y estado de verificación.

Una actualización crea un snapshot nuevo y nunca reescribe uno usado antes.

## Consecuencias

- Las evaluaciones históricas pueden reconstruirse.
- La aplicación puede detectar información vencida o contradictoria.
- Aumenta el almacenamiento y la necesidad de políticas de retención.
- Los adaptadores deben producir snapshots mediante contratos verificables.
