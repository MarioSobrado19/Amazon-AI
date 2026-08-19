# Caso de Estudio Oriva #0001

> **INTERNAL / CONFIDENTIAL — ORIVA.** Paquete de trabajo para revisión humana.
> No es material público de marketing ni debe publicarse fuera del repositorio
> autorizado sin una revisión específica de propiedad intelectual y divulgación.

Estado inicial: `HOLD — evidence acquisition`. Este estado no es una
recomendación de compra ni una invalidación de oportunidades. Indica que todavía
no existe evidencia suficiente para seleccionar un `BusinessPath`, generar
candidatos de inversión o arriesgar capital.

## Propósito

Este paquete congela antes de investigar el contrato del primer experimento de
self-dogfooding de Oriva. El experimento comprobará si el sistema puede llevar
un objetivo económico hasta una decisión comercial trazable, conservadora y
explicable. No obliga a encontrar un producto y acepta como resultado correcto
que la evidencia no justifique arriesgar dinero.

El caso es un contenedor documental/versionado, no una entidad nueva de Domain.
Los conceptos persistentes siguen siendo los ya existentes: `Objective`,
`GoalContextSnapshot`, `CandidateBusinessPath`, `BusinessPath`, `Investigation`,
`ResearchNeed`, `ResearchQuestion`, `EvidenceRecord`, `ResearchFinding`,
`EvidenceConflict`, `ResearchPlan`, `ResearchPlanAssessment`, Opportunity Graph
y decisión humana. Un `BusinessPath` solo podrá persistirse mediante la acción
humana explícita ya exigida por la arquitectura.

## Artefactos congelados

- `case_spec_v1.json`: condiciones, unknowns, preferencias, restricciones,
  escalones, límites y reglas de fuentes.
- `decision_policy_v1.md`: semántica y criterios GO/HOLD/STOP.
- `ledger_schema_v1.json`: cadena auditable y reglas de versionado inmutable.
- `ledger_v1.csv`: ledger inicial; registra el estado de conocimiento sin
  presentar hipótesis como datos.
- `reverse_economics_v1.md`: método de cálculo hacia atrás y política de datos
  faltantes.
- `capability_map_v1.md`: qué puede investigar Oriva hoy y qué sigue bloqueado.
- `research_plan_v1.json`: primer plan de adquisición de evidencia.
- `experiment_metrics_v1.json`: métricas de producto y resultados reales,
  inicialmente en cero cuando corresponde.
- `publication_template_v1.md`: formato futuro que separa simulación de hechos.
- `git_isolation_v1.md`: aislamiento respecto de Sprint 41.
- `evidence_acquisition_roadmap_v1.md`: prioridades documentales para salir de
  HOLD, sin implementar fuentes ni conexiones.

## Reglas de evolución

Los archivos `*_v1` no se reescriben después de iniciar la investigación. Una
modificación material crea `*_v2`, declara `supersedes_version`, conserva la
versión anterior y explica el motivo. Los registros del ledger son append-only;
una corrección agrega un registro que referencia al anterior.

No se selecciona candidato para inversión en esta versión. No se hizo compra,
venta, listing, contacto externo, apertura de cuenta ni gasto.
