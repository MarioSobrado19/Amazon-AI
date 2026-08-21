# Documentación de Oriva

## Arquitectura de dominio

- [Modelo de dominio oficial](domain/ORIVA_DOMAIN_MODEL.md)
- [Adaptación del Opportunity Engine](domain/OPPORTUNITY_ADAPTER.md)
- [Arquitectura de Marketplace y modelos operativos](architecture/MARKETPLACE_BUSINESS_MODEL_ARCHITECTURE.md)
- [Arquitectura Goal-to-Business y Opportunity Graph](architecture/GOAL_TO_BUSINESS_OPPORTUNITY_GRAPH_ARCHITECTURE.md)
- [Arquitectura de orquestación de investigación](architecture/RESEARCH_ORCHESTRATION_ARCHITECTURE.md)
- [Arquitectura Opportunity/Product Discovery V1](architecture/OPPORTUNITY_PRODUCT_DISCOVERY_V1.md)

## Integraciones

- [Diseño de integración Amazon US](integrations/AMAZON_US_INTEGRATION_DESIGN.md)
- [Amazon US Marketplace Conditions Capability V1](integrations/AMAZON_US_MARKETPLACE_CONDITIONS_V1.md)
- [Wikimedia Pageviews Demand Interest Capability V1](integrations/WIKIMEDIA_PAGEVIEWS_DEMAND_INTEREST_V1.md)
- [Library of Congress Documentary Presence Experiment](integrations/LIBRARY_OF_CONGRESS_DOCUMENTARY_PRESENCE_EXPERIMENT.md)
- [Evaluación de fuentes comerciales para Competition Research V1](integrations/COMPETITION_COMMERCIAL_SOURCE_EVALUATION.md)
- [Investigación de fuentes para Opportunity/Product Discovery V1](integrations/OPPORTUNITY_DISCOVERY_SOURCE_RESEARCH_V1.md)
- [Adquisición de fuente comercial para Discovery V1](integrations/COMMERCIAL_DISCOVERY_SOURCE_ACQUISITION_V1.md)
- [Caso de Estudio Oriva #0001](case-studies/oriva-0001/README.md)

## Architecture Decision Records

- [ADR-001: Oportunidad como entidad central](adr/ADR-001-opportunity-central-entity.md)
- [ADR-002: Recomendación y Decisión separadas](adr/ADR-002-recommendation-decision-separation.md)
- [ADR-003: Resultados inmutables y versionados](adr/ADR-003-immutable-versioned-results.md)
- [ADR-004: Core independiente de Amazon](adr/ADR-004-core-independence.md)
- [ADR-005: Adaptadores anticorrupción](adr/ADR-005-anticorruption-adapters.md)
- [ADR-006: Evidencia trazable](adr/ADR-006-evidence-traceability.md)
- [ADR-007: BusinessModel como concepto oficial](adr/ADR-007-business-model-domain-concept.md)
- [ADR-008: OpportunityScenario](adr/ADR-008-opportunity-scenario.md)
- [ADR-009: Snapshots de condiciones](adr/ADR-009-marketplace-condition-snapshots.md)
- [ADR-010: Separación de motores](adr/ADR-010-marketplace-business-decision-engine-separation.md)
- [ADR-011: Comparación multidimensional](adr/ADR-011-multidimensional-business-model-comparison.md)
- [ADR-012: Separación entre educación y políticas](adr/ADR-012-education-policy-separation.md)
- [ADR-013: IA explicadora, no fuente de verdad](adr/ADR-013-ai-explainer-not-source-of-truth.md)
- [ADR-014: Vigencia por tipo de información](adr/ADR-014-information-freshness-strategy.md)
- [ADR-015: Objetivo como raíz de Goal-to-Business](adr/ADR-015-goal-root.md)
- [ADR-016: CandidateBusinessPath y BusinessPath](adr/ADR-016-candidate-and-business-path.md)
- [ADR-017: BusinessPath y OpportunityScenario](adr/ADR-017-business-path-opportunity-scenario.md)
- [ADR-018: GoalContextSnapshot inmutable](adr/ADR-018-goal-context-snapshot.md)
- [ADR-019: PathAssessment multidimensional](adr/ADR-019-multidimensional-path-assessment.md)
- [ADR-020: Opportunity Graph no canónico](adr/ADR-020-opportunity-graph-projection.md)
- [ADR-021: EvidenceRelation trazable](adr/ADR-021-evidence-relation.md)
- [ADR-022: Goal-to-Business como orquestador](adr/ADR-022-goal-to-business-orchestrator.md)
- [ADR-023: Opportunity Matching opt-in](adr/ADR-023-opportunity-matching-opt-in.md)
- [ADR-024: Research Orchestrator coordina, no investiga](adr/ADR-024-research-orchestrator-coordinator.md)
- [ADR-025: ResearchPlan y ResearchTask](adr/ADR-025-research-plan-task-contracts.md)
- [ADR-026: Identidad semántica y ejecución](adr/ADR-026-research-semantic-execution-identity.md)
- [ADR-027: Reutilización de evidencia](adr/ADR-027-research-evidence-reuse.md)
- [ADR-028: DAG de tareas de investigación](adr/ADR-028-research-task-dag.md)
- [ADR-029: Fallos parciales](adr/ADR-029-research-partial-failures.md)
- [ADR-030: Freshness delegada](adr/ADR-030-research-freshness-delegation.md)
- [ADR-031: Aislamiento de evidencia](adr/ADR-031-research-evidence-isolation.md)
- [ADR-032: ResearchCapability ports](adr/ADR-032-research-capability-ports.md)
- [ADR-033: Discovery anterior a Opportunity](adr/ADR-033-opportunity-discovery-pre-opportunity-contract.md)

## Pilotos

- [Checklist de sesión piloto](PILOT_CHECKLIST.md)
