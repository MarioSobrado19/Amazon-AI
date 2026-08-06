# ADR-001 — Oportunidad como entidad central

- **Estado:** aceptado
- **Fecha:** 2026-08-06

## Contexto

Un Producto por sí solo no representa una posibilidad comercial. La evaluación
depende de supuestos, mercado, proveedor, momento y evidencia disponible.

## Decisión

`Oportunidad` será la entidad central de evaluación. Referenciará un Producto y,
cuando estén disponibles, Marketplace, Proveedor, Investigaciones y Resultados.
Marketplace podrá permanecer ausente durante exploración e investigación.

## Consecuencias

- Un mismo Producto puede originar varias Oportunidades.
- Los cambios de precio o mercado no alteran la identidad del Producto.
- Los motores comparten una unidad de evaluación consistente.
- La ausencia de contexto comercial reduce confianza y limita transiciones.

