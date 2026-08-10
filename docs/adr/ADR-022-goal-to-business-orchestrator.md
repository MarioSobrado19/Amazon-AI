# ADR-022 — Goal-to-Business como orquestador

- **Estado:** aceptado
- **Fecha:** 2026-08-10

## Contexto

Convertir un objetivo en rutas candidatas requiere coordinar capacidades de
Marketplace, Business Model, Opportunity y Decision sin absorber sus reglas ni
fabricar información para completar caminos.

## Decisión

Goal-to-Business será un orquestador de Application. Consumirá contratos y
resultados existentes, aplicará políticas explícitas de elegibilidad y ensamblará
`CandidateBusinessPath`. No calculará métricas financieras, no decidirá por el
usuario y no inventará oportunidades, proveedores, demanda o competencia.

## Consecuencias

- Cada motor conserva su responsabilidad.
- Un camino puede quedar incompleto o no generarse cuando falte evidencia.
- Las reglas de orquestación serán versionadas, reproducibles y explicables.
- La persistencia de un BusinessPath seguirá requiriendo una acción humana.
