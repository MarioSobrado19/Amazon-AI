# ADR-004 — Independencia del Core respecto de Amazon y fuentes externas

- **Estado:** aceptado
- **Fecha:** 2026-08-06

## Contexto

Oriva puede incorporar Amazon, otros marketplaces y múltiples proveedores de
datos. Convertir los conceptos de una fuente en el modelo central limitaría la
evolución y propagaría cambios externos.

## Decisión

El Core utilizará identificadores y conceptos propios. ASIN, SKU, respuestas de
APIs y formatos CSV serán referencias externas traducidas. Marketplace será una
capacidad opcional durante exploración e investigación.

## Consecuencias

- Oriva puede admitir nuevos mercados sin redefinir el Core.
- Los motores no dependen de clientes de APIs.
- Las particularidades de Amazon permanecen fuera del dominio permanente.
- La información externa siempre conserva fuente y vigencia.

