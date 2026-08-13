import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from application.business_path_service import promote_candidate_business_path
from application.opportunity_graph_service import project_opportunity_graph
from domain.contracts import CandidateBusinessPath, EvidenceRelation, PathAssessment
from domain.entities import (
    BusinessModel, Marketplace, MarketplaceConditionSnapshot, Objective,
    Opportunity, OpportunityScenario, Product, Recommendation, Result,
)
from domain.enums import (
    CandidatePathState, ConfidenceLevel, DecisionState, EvidenceRelationType,
    EvidenceType, FreshnessStatus, GraphNodeType, OperationalLoad,
    PathPromotionAction, VerificationStatus,
)
from domain.exceptions import DomainValidationError
from domain.value_objects import DomainNodeReference, GoalContextSnapshot, Region


NOW = datetime(2026, 8, 12, 12, tzinfo=timezone.utc)
LATER = NOW + timedelta(hours=1)
MARKET_ID = "11111111-1111-4111-8111-111111111111"
MODEL_ID = "22222222-2222-4222-8222-222222222222"
SCENARIO_ID = "33333333-3333-4333-8333-333333333333"
CANDIDATE_ID = "44444444-4444-4444-8444-444444444444"


def fixtures(*, expired=False):
    objective = Objective("goal-1", "Construir un negocio con recursos limitados")
    product = Product("product-1", "Producto X")
    result = Result("result-1", "ROI", 72.5, EvidenceType.ESTIMATE, "motor financiero", ConfidenceLevel.MEDIUM, NOW, "1")
    assumption = Result("assumption-1", "Demanda por confirmar", True, EvidenceType.ASSUMPTION, "usuario", ConfidenceLevel.LOW, NOW, "1")
    opportunity = Opportunity("opportunity-1", product, MARKET_ID, financial_context=(result,), evaluated_at=NOW)
    marketplace = Marketplace(MARKET_ID, "Marketplace Y", Region("US"), "USD", "fuente oficial", NOW, "1")
    model = BusinessModel(
        MODEL_ID, "Modelo Z", Region("US"), ConfidenceLevel.MEDIUM, "1",
        marketplace_id=MARKET_ID, source="fuente oficial", valid_from=NOW,
        operational_load=OperationalLoad.MEDIUM,
    )
    freshness = FreshnessStatus.EXPIRED if expired else FreshnessStatus.CURRENT
    snapshot = MarketplaceConditionSnapshot(
        "55555555-5555-4555-8555-555555555555", marketplace, Region("US"),
        "tarifa", {"porcentaje": 15}, "fuente oficial", NOW, NOW,
        freshness, ConfidenceLevel.HIGH, VerificationStatus.VERIFIED, "1",
        NOW + timedelta(days=1) if expired else NOW + timedelta(days=30),
    )
    scenario = OpportunityScenario(
        SCENARIO_ID, opportunity, marketplace, model, Region("US"), NOW,
        conditions=(snapshot,), costs=(result,), assumptions=(assumption,),
    )
    context = GoalContextSnapshot("goal-1", NOW, "1", region=Region("US"))
    candidate = CandidateBusinessPath(
        CANDIDATE_ID, "goal-1", context, PathAssessment((), ConfidenceLevel.LOW, "1"),
        CandidatePathState.INCOMPLETE, ConfidenceLevel.LOW, "1",
        marketplace=marketplace, business_model=model, scenario=scenario,
        available_evidence=(result,), condition_snapshots=(snapshot,),
        missing_evidence=("demanda", "competencia"), assumptions=(assumption,),
        risks=("Información comercial incompleta.",),
    )
    path = promote_candidate_business_path(
        candidate, action=PathPromotionAction.SAVE, actor_id="user-1", promoted_at=NOW
    ).business_path
    recommendation = Recommendation(
        "recommendation-1", DecisionState.INVESTIGATE, "Investigar", "Faltan datos comerciales.",
        ConfidenceLevel.LOW, opportunity_id=opportunity.opportunity_id,
        evidence=(result,), limitations=("No valida demanda.",), created_at=NOW,
    )
    return locals()


def graph(data=None, **overrides):
    data = data or fixtures()
    values = {
        "generated_at": NOW,
        "objective": data["objective"],
        "candidate_paths": (data["candidate"],),
        "business_paths": (data["path"],),
        "scenarios": (data["scenario"],),
        "opportunities": (data["opportunity"],),
        "products": (data["product"],),
        "marketplaces": (data["marketplace"],),
        "business_models": (data["model"],),
        "results": (data["result"], data["assumption"]),
        "recommendations": (data["recommendation"],),
    }
    values.update(overrides)
    return project_opportunity_graph(**values)


class DomainNodeReferenceTests(unittest.TestCase):
    def test_node_id_es_determinista_y_versionado(self):
        first = DomainNodeReference(GraphNodeType.PRODUCT, "p-1", "Producto", "1")
        same = DomainNodeReference(GraphNodeType.PRODUCT, "p-1", "Otro label", "1")
        changed = DomainNodeReference(GraphNodeType.PRODUCT, "p-1", version="2")
        self.assertEqual(first.node_id, same.node_id)
        self.assertNotEqual(first.node_id, changed.node_id)

    def test_metadata_es_profunda_inmutable_y_serializable(self):
        source = {"contexto": {"valores": [1, 2]}}
        node = DomainNodeReference(GraphNodeType.PRODUCT, "p-1", metadata=source)
        source["contexto"]["valores"].append(3)
        serialized = node.to_dict()
        serialized["metadata"]["contexto"]["valores"].append(4)
        self.assertEqual(node.metadata.to_dict(), {"contexto": {"valores": [1, 2]}})

    def test_metadata_rechaza_secretos_y_node_id_falso(self):
        with self.assertRaises(DomainValidationError):
            DomainNodeReference(GraphNodeType.PRODUCT, "p-1", metadata={"token": "x"})
        with self.assertRaises(DomainValidationError):
            DomainNodeReference(GraphNodeType.PRODUCT, "p-1", metadata={"auth": {"access_token": "x"}})
        for key in (
            "REFRESH_TOKEN", "Authorization", "bearer", "CLIENT_SECRET",
            "api_key", "ApiKey", "PASSWORD", "Credential", "E-MAIL",
        ):
            with self.subTest(key=key), self.assertRaises(DomainValidationError):
                DomainNodeReference(GraphNodeType.PRODUCT, "p-1", metadata={key: "x"})
        with self.assertRaises(DomainValidationError):
            DomainNodeReference(GraphNodeType.PRODUCT, "p-1", node_id="incorrecto")

    def test_referencia_es_inmutable_y_compara_por_valor(self):
        node = DomainNodeReference(GraphNodeType.OBJECTIVE, "goal-1")
        self.assertEqual(node, DomainNodeReference(GraphNodeType.OBJECTIVE, "goal-1"))
        with self.assertRaises(FrozenInstanceError):
            node.domain_id = "otro"

    def test_label_y_metadata_de_presentacion_no_cambian_identidad(self):
        first = DomainNodeReference(
            GraphNodeType.PRODUCT, "p-1", "Nombre A", "1", {"display": "compact"}
        )
        second = DomainNodeReference(
            GraphNodeType.PRODUCT, "p-1", "Nombre B", "1", {"display": "expanded"}
        )
        self.assertEqual(first.node_id, second.node_id)


class EvidenceRelationTests(unittest.TestCase):
    def relation(self, evidence_type=EvidenceType.DATA, freshness=None):
        return EvidenceRelation(
            DomainNodeReference(GraphNodeType.RESULT, "r-1"),
            DomainNodeReference(GraphNodeType.OPPORTUNITY, "o-1"),
            EvidenceRelationType.SUPPORTS, evidence_type, "fuente",
            ConfidenceLevel.MEDIUM, NOW, "Explicación trazable", "1", freshness,
        )

    def test_relacion_determinista_y_direccional(self):
        first = self.relation()
        self.assertEqual(first.relation_id, self.relation().relation_id)
        reverse = EvidenceRelation(first.target_node, first.source_node, first.relation_type, EvidenceType.DATA, "fuente", ConfidenceLevel.MEDIUM, NOW, "Explicación trazable", "1")
        self.assertNotEqual(first.relation_id, reverse.relation_id)

    def test_evidencia_materialmente_distinta_produce_relaciones_distintas(self):
        first = self.relation(EvidenceType.DATA)
        estimate = self.relation(EvidenceType.ESTIMATE)
        assumption = self.relation(EvidenceType.ASSUMPTION)
        self.assertEqual(len({first.relation_id, estimate.relation_id, assumption.relation_id}), 3)

    def test_fecha_de_evidencia_cambia_identidad_pero_generacion_no_participa(self):
        first = self.relation()
        later = EvidenceRelation(
            first.source_node, first.target_node, first.relation_type,
            first.evidence_type, first.source, first.confidence, LATER,
            first.explanation, first.version,
        )
        self.assertNotEqual(first.relation_id, later.relation_id)

    def test_orden_de_supuestos_y_limitaciones_no_cambia_identidad(self):
        source = DomainNodeReference(GraphNodeType.RESULT, "r-1")
        target = DomainNodeReference(GraphNodeType.OPPORTUNITY, "o-1")
        first = EvidenceRelation(
            source, target, EvidenceRelationType.SUPPORTS, EvidenceType.ASSUMPTION,
            "fuente", ConfidenceLevel.LOW, NOW, "Explicación", "1", None,
            ("A", "B"), ("C", "D"),
        )
        second = EvidenceRelation(
            source, target, EvidenceRelationType.SUPPORTS, EvidenceType.ASSUMPTION,
            "fuente", ConfidenceLevel.LOW, NOW, "Explicación", "1", None,
            ("B", "A"), ("D", "C"),
        )
        self.assertEqual(first.relation_id, second.relation_id)

    def test_conserva_data_estimate_assumption_y_freshness(self):
        for kind in EvidenceType:
            self.assertEqual(self.relation(kind).evidence_type, kind)
        self.assertEqual(self.relation(freshness=FreshnessStatus.EXPIRED).freshness, FreshnessStatus.EXPIRED)

    def test_fecha_sin_timezone_y_autorelacion_se_rechazan(self):
        node = DomainNodeReference(GraphNodeType.RESULT, "r-1")
        with self.assertRaises(DomainValidationError):
            EvidenceRelation(node, DomainNodeReference(GraphNodeType.OPPORTUNITY, "o-1"), EvidenceRelationType.SUPPORTS, EvidenceType.DATA, "fuente", ConfidenceLevel.HIGH, datetime(2026, 1, 1), "x", "1")
        with self.assertRaises(DomainValidationError):
            EvidenceRelation(node, node, EvidenceRelationType.SUPPORTS, EvidenceType.DATA, "fuente", ConfidenceLevel.HIGH, NOW, "x", "1")

    def test_serializacion_e_inmutabilidad(self):
        relation = self.relation(EvidenceType.ASSUMPTION)
        self.assertEqual(relation.to_dict()["evidence_type"], "supuesto")
        with self.assertRaises(FrozenInstanceError):
            relation.source = "otra"


class OpportunityGraphProjectorTests(unittest.TestCase):
    def test_grafo_solo_objective_es_valido(self):
        item = fixtures()["objective"]
        result = project_opportunity_graph(generated_at=NOW, objective=item)
        self.assertEqual(result.root_node.node_type, GraphNodeType.OBJECTIVE)
        self.assertEqual(len(result.nodes), 1)
        self.assertEqual(result.relations, ())

    def test_objective_y_candidate_crean_relacion(self):
        data = fixtures()
        result = project_opportunity_graph(generated_at=NOW, objective=data["objective"], candidate_paths=(data["candidate"],))
        self.assertIn(EvidenceRelationType.PURSUES, {x.relation_type for x in result.relations})
        self.assertIn("demanda", result.missing_information)

    def test_objective_y_business_path_crean_relacion(self):
        data = fixtures()
        result = project_opportunity_graph(generated_at=NOW, objective=data["objective"], business_paths=(data["path"],))
        self.assertIn(EvidenceRelationType.PURSUES, {x.relation_type for x in result.relations})

    def test_business_path_scenario_marketplace_y_modelo(self):
        result = graph()
        types = {x.relation_type for x in result.relations}
        self.assertTrue({EvidenceRelationType.USES_SCENARIO, EvidenceRelationType.TARGETS_MARKETPLACE, EvidenceRelationType.CONSIDERS_BUSINESS_MODEL}.issubset(types))

    def test_scenario_evalua_opportunity_y_opportunity_concerns_product(self):
        result = graph()
        types = {x.relation_type for x in result.relations}
        self.assertIn(EvidenceRelationType.EVALUATES, types)
        self.assertIn(EvidenceRelationType.CONCERNS_PRODUCT, types)

    def test_result_conserva_tipo_de_evidencia(self):
        result = graph()
        relations = [x for x in result.relations if x.source_node.node_type is GraphNodeType.RESULT]
        self.assertIn(EvidenceType.ESTIMATE, {x.evidence_type for x in relations})
        self.assertIn(EvidenceType.ASSUMPTION, {x.evidence_type for x in relations})

    def test_recommendation_se_marca_como_derivada_no_hecho(self):
        result = graph()
        relation = next(x for x in result.relations if x.source_node.node_type is GraphNodeType.RECOMMENDATION)
        self.assertEqual(relation.relation_type, EvidenceRelationType.DERIVED_FROM)
        self.assertEqual(relation.evidence_type, EvidenceType.ESTIMATE)

    def test_evidencia_expirada_se_conserva_y_advierte(self):
        result = graph(fixtures(expired=True))
        self.assertTrue(any("vencida" in warning.lower() for warning in result.warnings))
        self.assertTrue(any(relation.freshness is FreshnessStatus.EXPIRED for relation in result.relations))
        self.assertTrue(any(node.node_type is GraphNodeType.MARKETPLACE for node in result.nodes))

    def test_business_path_sin_objetos_referenciados_declara_faltantes(self):
        data = fixtures()
        result = project_opportunity_graph(generated_at=NOW, objective=data["objective"], business_paths=(data["path"],))
        self.assertTrue(any(item.startswith("opportunity_scenario:") for item in result.missing_information))
        self.assertTrue(any(item.startswith("marketplace:") for item in result.missing_information))

    def test_grafo_parcial_no_inventa_componentes(self):
        data = fixtures()
        result = project_opportunity_graph(generated_at=NOW, opportunities=(data["opportunity"],))
        types = {node.node_type for node in result.nodes}
        self.assertEqual(types, {GraphNodeType.OPPORTUNITY, GraphNodeType.PRODUCT, GraphNodeType.RESULT})
        self.assertNotIn(GraphNodeType.MARKETPLACE, types)

    def test_graph_id_no_depende_de_generated_at(self):
        first = graph(generated_at=NOW)
        second = graph(generated_at=LATER)
        self.assertEqual(first.graph_id, second.graph_id)
        self.assertNotEqual(first.generated_at, second.generated_at)

    def test_labels_y_metadata_no_esenciales_no_cambian_graph_id(self):
        data = fixtures()
        first = graph(data)
        changed_product = Product(data["product"].product_id, "Etiqueta visual distinta")
        changed_opportunity = Opportunity(
            data["opportunity"].opportunity_id,
            changed_product,
            MARKET_ID,
            financial_context=(data["result"],),
            evaluated_at=NOW,
        )
        second = graph(
            data,
            opportunities=(changed_opportunity,),
            products=(changed_product,),
            scenarios=(),
            candidate_paths=(),
            business_paths=(),
            marketplaces=(),
            business_models=(),
            recommendations=(),
        )
        comparable_first = graph(
            data,
            opportunities=(data["opportunity"],),
            products=(data["product"],),
            scenarios=(),
            candidate_paths=(),
            business_paths=(),
            marketplaces=(),
            business_models=(),
            recommendations=(),
        )
        self.assertEqual(comparable_first.graph_id, second.graph_id)
        self.assertNotEqual(first.graph_id, second.graph_id)

    def test_graph_id_cambia_con_evidencia_semantica_real(self):
        data = fixtures()
        first = graph(data)
        changed = Result(
            "result-1", "ROI", 75.0, EvidenceType.ESTIMATE,
            "otra fuente", ConfidenceLevel.HIGH, LATER, "2",
        )
        changed_opportunity = Opportunity(
            data["opportunity"].opportunity_id, data["product"], MARKET_ID,
            financial_context=(changed,), evaluated_at=NOW,
        )
        second = graph(
            data,
            opportunities=(changed_opportunity,),
            results=(changed, data["assumption"]),
            scenarios=(), candidate_paths=(), business_paths=(), recommendations=(),
        )
        baseline = graph(
            data,
            opportunities=(data["opportunity"],),
            results=(data["result"], data["assumption"]),
            scenarios=(), candidate_paths=(), business_paths=(), recommendations=(),
        )
        self.assertNotEqual(baseline.graph_id, second.graph_id)
        self.assertNotEqual(first.graph_id, second.graph_id)

    def test_nueva_version_real_de_entidad_cambia_graph_id(self):
        data = fixtures()
        first = project_opportunity_graph(generated_at=NOW, marketplaces=(data["marketplace"],))
        revised = Marketplace(
            MARKET_ID, data["marketplace"].name, Region("US"), "USD",
            "fuente oficial", NOW, "2",
        )
        second = project_opportunity_graph(generated_at=LATER, marketplaces=(revised,))
        self.assertNotEqual(first.graph_id, second.graph_id)

    def test_orden_de_entrada_no_cambia_grafo(self):
        data = fixtures()
        extra = Result("result-2", "Margen", 30, EvidenceType.ESTIMATE, "motor", recorded_at=NOW)
        first = graph(data, results=(data["result"], extra))
        second = graph(data, results=(extra, data["result"]))
        self.assertEqual(first.graph_id, second.graph_id)

    def test_nodos_y_relaciones_duplicados_se_eliminan(self):
        data = fixtures()
        result = graph(data, opportunities=(data["opportunity"], data["opportunity"]), results=(data["result"], data["result"]))
        self.assertEqual(len(result.nodes), len({x.node_id for x in result.nodes}))
        self.assertEqual(len(result.relations), len({x.relation_id for x in result.relations}))

    def test_evidencias_distintas_sobre_mismo_destino_no_se_deduplican(self):
        data = fixtures()
        second_result = Result(
            "result-2", "ROI alternativo", 70.0, EvidenceType.ESTIMATE,
            "segunda fuente", ConfidenceLevel.LOW, LATER, "1",
        )
        result = graph(data, results=(data["result"], second_result))
        relations = [
            item for item in result.relations
            if item.source_node.node_type is GraphNodeType.RESULT
            and item.target_node.node_type is GraphNodeType.BUSINESS_PATH
        ]
        self.assertEqual(len({item.relation_id for item in relations}), len(relations))

    def test_snapshot_es_serializable_y_profunda_inmutable(self):
        result = graph()
        payload = result.to_dict()
        json.dumps(payload)
        payload["nodes"].clear()
        self.assertTrue(result.nodes)
        with self.assertRaises(FrozenInstanceError):
            result.graph_id = "otro"

    def test_generated_at_requiere_timezone(self):
        with self.assertRaises(DomainValidationError):
            project_opportunity_graph(generated_at=datetime(2026, 1, 1), objective=fixtures()["objective"])

    def test_entrada_invalida_se_rechaza(self):
        with self.assertRaises(DomainValidationError):
            project_opportunity_graph(generated_at=NOW, products=(object(),))

    def test_no_muta_entidades_originales(self):
        data = fixtures()
        before = data["candidate"].to_dict()
        graph(data)
        self.assertEqual(data["candidate"].to_dict(), before)

    def test_salida_no_contiene_score_ranking_winner_ni_orden_de_inversion(self):
        payload = json.dumps(graph().to_dict(), ensure_ascii=False).lower()
        for forbidden in ("score", "ranking", "winner", "debes invertir", "debes comprar", "likely_profitable", "best_for", "high_demand"):
            self.assertNotIn(forbidden, payload)

    def test_tipos_v1_son_genericos_y_estables(self):
        values = {item.value for item in GraphNodeType}
        self.assertEqual(len(values), 10)
        self.assertFalse(any("amazon" in value for value in values))

    def test_relaciones_v1_son_genericas_y_sin_inferencia_oculta(self):
        values = {item.value for item in EvidenceRelationType}
        self.assertFalse({"similar_to", "best_for", "likely_profitable", "recommended", "high_demand"}.intersection(values))
        self.assertIn("provides_evidence_for", values)

    def test_contexto_de_otro_objetivo_se_rechaza(self):
        data = fixtures()
        other = GoalContextSnapshot("goal-2", NOW, "1")
        with self.assertRaises(DomainValidationError):
            graph(data, goal_context=other)


class ArchitectureProtectionTests(unittest.TestCase):
    def test_domain_no_importa_capas_externas(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1] / "domain"
        text = "\n".join(path.read_text() for path in root.rglob("*.py"))
        for forbidden in ("from application", "import application", "streamlit", "networkx", "neo4j"):
            self.assertNotIn(forbidden, text.lower())

    def test_projector_no_contiene_formulas_scores_o_matching(self):
        from pathlib import Path
        text = (Path(__file__).resolve().parents[1] / "application" / "opportunity_graph_service.py").read_text().lower()
        for forbidden in ("calculate_roi", "calcular_rentabilidad", "opportunity_score", "networkx", "neo4j", "matching"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
