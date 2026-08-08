# ADR-010 — Separación de motores de marketplace, modelo y decisión

- **Estado:** aceptado
- **Fecha:** 2026-08-08

## Contexto

Descubrir opciones, evaluar su ajuste y recomendar un siguiente paso son
responsabilidades diferentes. Mezclarlas ocultaría reglas y dificultaría la
incorporación de canales nuevos.

## Decisión

- Marketplace Engine responde qué opciones existen y bajo qué condiciones.
- Business Model Engine responde cómo encajan con el usuario y el proyecto.
- Decision Engine responde cuál es el siguiente paso razonable.

Ningún motor absorberá responsabilidades de los demás. Sus intercambios se
realizarán mediante contratos versionados y Resultados trazables.

## Consecuencias

- Las reglas tienen propietarios claros y pueden probarse por separado.
- Business Model Assessment es evidencia, no Decisión.
- El usuario conserva siempre la decisión final.
- Se evita duplicar políticas externas dentro del Decision Engine.
