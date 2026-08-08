# ADR-008 — OpportunityScenario para contextos operativos comparables

- **Estado:** aceptado
- **Fecha:** 2026-08-08

## Contexto

Una Opportunity puede evaluarse con diferentes marketplaces, modelos
operativos, proveedores, costos, condiciones y supuestos. Añadir directamente
un modelo a Opportunity impediría comparar alternativas sin mutar su contexto.

## Decisión

Se adopta conceptualmente `OpportunityScenario`. Cada escenario referenciará una
Opportunity y una combinación específica de Marketplace, región, BusinessModel,
Proveedor opcional, costos, snapshots externos, momento y supuestos.

No se añadirá por ahora `business_model_id` directamente a Opportunity.

## Consecuencias

- Una Opportunity conserva identidad e historial.
- Pueden existir múltiples escenarios comparables y versionados.
- Cambiar de modelo no modifica resultados históricos.
- La implementación futura debe controlar proliferación y deduplicación de
  escenarios.
