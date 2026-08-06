# ADR-002 — Separación entre Recomendación y Decisión

- **Estado:** aceptado
- **Fecha:** 2026-08-06

## Contexto

Oriva debe apoyar decisiones sin sustituir al usuario. Equiparar una salida del
motor con una decisión ocultaría quién eligió y qué riesgos aceptó.

## Decisión

`Recomendación` y `Decisión` serán entidades distintas. La Recomendación registra
orientación, evidencia, reglas, confianza y limitaciones. La Decisión registra la
elección humana, su responsable, justificación y contexto.

## Consecuencias

- El usuario conserva control explícito.
- Una recomendación puede aceptarse, rechazarse o ignorarse.
- El historial puede explicar diferencias entre lo recomendado y lo decidido.
- Ningún motor ejecutará compras, inversiones o pruebas por sí mismo.

