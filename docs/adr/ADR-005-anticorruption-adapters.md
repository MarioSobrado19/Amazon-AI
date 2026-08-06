# ADR-005 — Adaptadores anticorrupción para integraciones

- **Estado:** aceptado
- **Fecha:** 2026-08-06

## Contexto

APIs, archivos y proveedores externos usan vocabularios, estructuras y ciclos de
cambio que no deben filtrarse al dominio.

## Decisión

Toda integración atravesará un adaptador anticorrupción. El adaptador validará,
traducirá y etiquetará la información con fuente, fecha, vigencia y calidad antes
de entregarla a Application o al dominio.

## Consecuencias

- Una integración puede reemplazarse sin modificar motores.
- Los errores externos se traducen a contratos internos.
- Se evita que formatos de terceros definan entidades centrales.
- Cada adaptador requiere pruebas contractuales propias.

