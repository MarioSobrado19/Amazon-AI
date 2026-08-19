# Aislamiento Git v1

- Sprint 41 permanece en el worktree `Amazon-AI-sprint40`, rama
  `feature/ebay-commercial-competition-capability-v1`.
- Antes de aislar, su HEAD era `40a852a7ccc7dcb23d066c1eb7e5792f85d3a9c5`
  y contenía un archivo tracked modificado y diez archivos untracked bajo
  documentación, infraestructura eBay, fixtures y pruebas.
- El worktree principal `main` estaba limpio y `main`, `origin/main` y su HEAD
  apuntaban al mismo commit `40a852a7ccc7dcb23d066c1eb7e5792f85d3a9c5`.
- Este caso usa un worktree separado, rama local
  `case-study/oriva-0001`, creado desde `main` limpio.
- Los archivos de Sprint 41 no se copiaron, conectaron ni modificaron aquí.
- El encargo inicial mantuvo la rama sin commits. El cierre controlado posterior
  autoriza commit del paquete, fast-forward seguro a `main` y push normal, pero
  prohíbe rebase, squash, force-push y cualquier modificación de Sprint 41.
