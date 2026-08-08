# ADR-007 — BusinessModel como concepto oficial del dominio

- **Estado:** aceptado
- **Fecha:** 2026-08-08

## Contexto

Oriva necesita representar formas de operar dentro de múltiples marketplaces.
Nombres como FBA, FBM o WFS son conceptos externos que no deben definir el Core.

## Decisión

`BusinessModel` será un concepto oficial y genérico del dominio. Representará
una forma concreta de operar dentro de un Marketplace, región y periodo. Los
programas particulares de cada canal serán registros traducidos por sus
adaptadores y catálogos, nunca tipos o reglas incorporados al Core.

## Consecuencias

- El Core permanece independiente de Amazon y otros canales.
- Cada marketplace puede ofrecer modelos con capacidades diferentes.
- Agregar un nuevo modelo externo no exige modificar la entidad genérica.
- BusinessModel debe conservar fuente, región, vigencia y confianza.
