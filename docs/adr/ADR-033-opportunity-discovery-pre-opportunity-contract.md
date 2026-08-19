# ADR-033 — Discovery es anterior a Opportunity

> **INTERNAL / CONFIDENTIAL — ORIVA.** Estado: propuesto para revisión.

## Contexto

`Opportunity` evalúa un `Product`; `CandidateBusinessPath` y
`OpportunityScenario` ya representan etapas posteriores. Discovery necesita
conservar semillas, señales y contradicciones antes de que exista Product válido.

## Decisión propuesta

Modelar `DiscoverySeed`, `DiscoverySignal` y `OpportunityHypothesis` primero como
contratos de Application reconstruibles. Una hipótesis no es Opportunity ni
candidato. Su identidad será determinista, sus señales tipadas, y su promoción
requerirá revisión explícita y ResearchNeeds. No se añadirá un score.

## Consecuencias

Domain, motores, fórmulas y UI permanecen intactos. `EvidenceRecord` se reutiliza
solo cuando hay sujeto estable; no se fabricará `subject_id` para encajar una
semilla. La estabilidad del contrato se probará antes de considerar adopción en
Domain.
