# ADR-012 — Separación entre educación y condiciones oficiales

- **Estado:** aceptado
- **Fecha:** 2026-08-08

## Contexto

La explicación debe adaptarse a la experiencia del usuario, mientras que
tarifas, políticas y requisitos deben permanecer fieles a fuentes oficiales.
Mezclarlos permitiría que una simplificación alterara una condición operativa.

## Decisión

`EducationalPath` será independiente de los snapshots oficiales. Explicará qué
es un modelo, cómo funciona, cómo empezar, responsabilidades, errores, métricas y
cuándo reconsiderarlo. Las condiciones oficiales conservarán tarifas,
políticas, restricciones, requisitos, disponibilidad, región y vigencia.

## Consecuencias

- Puede adaptarse el lenguaje sin modificar hechos.
- Ambos contenidos tendrán versiones y revisión propias.
- Las explicaciones deben enlazar las condiciones oficiales que utilicen.
- Contenido educativo desactualizado no sustituye evidencia operativa vigente.
