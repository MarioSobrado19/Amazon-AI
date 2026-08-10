# ADR-016 — CandidateBusinessPath y BusinessPath

- **Estado:** aceptado
- **Fecha:** 2026-08-10

## Contexto

La exploración puede producir muchas rutas tentativas. Persistirlas todas como
entidades oficiales contaminaría el historial y confundiría una posibilidad
generada con una ruta aceptada por el usuario.

## Decisión

`CandidateBusinessPath` será un contrato temporal, reconstruible y no
persistido por defecto. `BusinessPath` será una entidad persistente únicamente
cuando el usuario la guarde, seleccione o comience a investigar explícitamente.

## Consecuencias

- La exploración no llena el Core de candidatos efímeros.
- La persistencia exige intención humana explícita.
- `BusinessPath` tendrá identidad estable, versión e historial.
- Descartar un candidato no equivale a eliminar una decisión histórica.
