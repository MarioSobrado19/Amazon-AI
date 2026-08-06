# ADR-006 — Evidencia con fuente, vigencia y confianza

- **Estado:** aceptado
- **Fecha:** 2026-08-06

## Contexto

Una cifra aislada no permite saber si sigue vigente, de dónde procede ni cuánto
debe influir en una decisión. Esto es especialmente crítico para Demanda,
Competencia y condiciones comerciales.

## Decisión

Toda evidencia conservará fuente, fecha, vigencia, confianza, alcance y
limitaciones. Demanda y Competencia serán observaciones temporales ligadas a
Marketplace, región y periodo. Las condiciones de un Proveedor vivirán en
Cotizaciones versionadas futuras.

## Consecuencias

- La información desactualizada puede detectarse.
- Los motores reducen confianza cuando falta evidencia verificable.
- No se trasladan observaciones entre mercados o periodos implícitamente.
- Las recomendaciones pueden explicar exactamente qué evidencia utilizaron.

