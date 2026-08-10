# ADR-021 — EvidenceRelation trazable

- **Estado:** aceptado
- **Fecha:** 2026-08-10

## Contexto

Una relación del grafo puede ser un hecho verificado, una estimación o un
supuesto. Sin procedencia y vigencia, Oriva no puede explicar por qué conectó
dos conceptos ni evaluar si la relación sigue siendo utilizable.

## Decisión

Las relaciones relevantes usarán conceptualmente `EvidenceRelation` y
conservarán origen, destino, tipo de relación, EvidenceType, fuente, región,
fecha de consulta, vigencia/freshness, confianza, versión, supuestos y
restricciones cuando apliquen.

Una inferencia debe identificarse como tal y nunca presentarse como dato
verificado.

## Consecuencias

- Cada recomendación puede rastrearse hasta evidencia concreta.
- La ausencia, contradicción o expiración permanece visible.
- Nuevas evidencias no reescriben relaciones históricas usadas anteriormente.
- La IA puede explicar relaciones, pero no convertirse en su fuente de verdad.
