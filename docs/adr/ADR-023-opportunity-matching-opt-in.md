# ADR-023 — Opportunity Matching opt-in

- **Estado:** aceptado
- **Fecha:** 2026-08-10

## Contexto

Un matching futuro podría conectar compradores, vendedores, negocios,
fabricantes, proveedores y distribuidores. Esa capacidad puede revelar datos
comerciales o personales y generar inferencias sensibles.

## Decisión

Opportunity Matching será una capacidad futura, separada y voluntaria. Exigirá
consentimiento explícito, propósito declarado, minimización de datos, controles
de visibilidad, revocación, salida sencilla, explicación del match y decisión
humana final. No se implementa en este sprint.

## Consecuencias

- Los datos privados no entran al matching por defecto.
- Compartir una relación no autoriza recorrer todo el grafo del usuario.
- No se garantiza compatibilidad, acuerdo ni resultado económico.
- Antes de implementarlo se requerirán revisión legal, seguridad, retención,
  eliminación y mitigación de sesgos.
