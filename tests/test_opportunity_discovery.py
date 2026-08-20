import json
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from application.discovery_models import (
    DiscoveryRequest,
    DiscoveryRunStatus,
    DiscoverySignal,
    DiscoverySignalType,
    DiscoverySourceKind,
    DiscoverySourceResult,
    DiscoverySourceStatus,
    HypothesisIdentityKind,
    OpportunityHypothesisState,
)
from application.opportunity_discovery_service import discover_opportunity_hypotheses
from domain.entities import EvidenceRecord
from domain.enums import ConfidenceLevel, EvidenceType, FreshnessStatus, ResearchCategory, VerificationStatus
from domain.exceptions import DomainValidationError
from domain.value_objects import Region


NOW = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
FIXTURE = Path(__file__).parent / "fixtures" / "discovery" / "synthetic_signals.json"
CASE_STATUS = Path(__file__).parents[1] / "docs" / "case-studies" / "oriva-0001" / "case_status_v2.json"


def request(**changes):
    values = {
        "request_id": "oriva-case-0001-discovery-v1",
        "objective_id": "oriva-case-0001-objective",
        "generated_at": NOW,
        "region": Region("US"),
        "future_capital_ceiling_usd": 750,
        "currently_authorized_capital_usd": 0,
        "horizon_days": 90,
        "max_hypotheses": 10,
    }
    values.update(changes)
    return DiscoveryRequest(**values)


def evidence(identity="synthetic desk organizer"):
    return EvidenceRecord(
        "36b8b98e-c21c-5e10-a355-776b5c2c5ec5", "discovery_identity", identity,
        ResearchCategory.MARKETPLACE, EvidenceType.DATA,
        {"classification": "SYNTHETIC / NOT REAL EVIDENCE"},
        "Synthetic fixture", NOW, NOW, FreshnessStatus.CURRENT,
        VerificationStatus.VERIFIED, ConfidenceLevel.LOW, "fixture/1.0",
        region=Region("US"), limitations=("No es evidencia real.",),
    )


def signal(signal_type=DiscoverySignalType.CATALOG_PRESENCE, identity="synthetic desk organizer", **changes):
    values = {
        "signal_type": signal_type,
        "identity_kind": HypothesisIdentityKind.PRODUCT,
        "identity_value": identity,
        "source": "Synthetic discovery fixture",
        "source_kind": DiscoverySourceKind.FIXTURE,
        "observed_at": NOW,
        "retrieved_at": NOW,
        "freshness": FreshnessStatus.CURRENT,
        "verification_status": VerificationStatus.VERIFIED,
        "method_version": "fixture/1.0",
        "value": {"classification": "SYNTHETIC / NOT REAL EVIDENCE"},
        "region": Region("US"),
        "limitations": ("Fixture; no demuestra mercado real.",),
    }
    values.update(changes)
    return DiscoverySignal(**values)


class StaticSource:
    def __init__(self, source_id, result):
        self.source_id = source_id
        self.result = result

    def collect(self, _request):
        return self.result


def source_result(*signals, source_id="fixture-source", status=DiscoverySourceStatus.SUCCESS):
    return DiscoverySourceResult(source_id, status, NOW, signals)


class DiscoveryContractTests(unittest.TestCase):
    def test_taxonomia_completa_y_semantica_inmutable(self):
        self.assertEqual({item.value for item in DiscoverySignalType}, {
            "attention", "search_interest", "catalog_presence", "commercial_listing_presence",
            "price_observation", "category_activity", "marketplace_presence", "supply_signal",
            "macro_consumer_signal", "trend_change",
        })
        with self.assertRaises(FrozenInstanceError):
            signal().identity_value = "otro"

    def test_signal_id_determinista_y_cambio_material(self):
        self.assertEqual(signal().signal_id, signal().signal_id)
        self.assertNotEqual(signal().signal_id, signal(observed_at=NOW + timedelta(days=1), retrieved_at=NOW + timedelta(days=1)).signal_id)
        self.assertNotEqual(signal().signal_id, signal(signal_type=DiscoverySignalType.ATTENTION).signal_id)

    def test_timezone_y_provenance_obligatorias(self):
        with self.assertRaises(DomainValidationError):
            signal(observed_at=NOW.replace(tzinfo=None))
        with self.assertRaises(DomainValidationError):
            signal(source=" ")

    def test_evidence_record_asociado_se_conserva(self):
        item = signal(evidence_record=evidence())
        result = discover_opportunity_hypotheses(request(), (StaticSource("fixture", source_result(item)),), generated_at=NOW)
        hypothesis = result.hypotheses[0]
        self.assertEqual(hypothesis.evidence_records, (item.evidence_record,))
        self.assertEqual(hypothesis.to_dict()["evidence_ids"], [item.evidence_record.evidence_id])

    def test_fixture_identificado_como_no_real(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["classification"], "SYNTHETIC / NOT REAL EVIDENCE")
        result = discover_opportunity_hypotheses(request(), (StaticSource("fixture", source_result(signal())),), generated_at=NOW)
        self.assertFalse(result.real_hypotheses)
        self.assertIs(result.status, DiscoveryRunStatus.HOLD_EVIDENCE_ACQUISITION)

    def test_no_expone_score_ranking_winner_o_promocion(self):
        result = discover_opportunity_hypotheses(request(), (StaticSource("fixture", source_result(signal())),), generated_at=NOW)
        serialized = json.dumps(result.to_dict()).casefold()
        for forbidden in ("opportunity_score", "probability_of_success", "winner", "recommendation_to_buy", "businesspath"):
            self.assertNotIn(forbidden, serialized)


class DiscoveryPipelineTests(unittest.TestCase):
    def run_with(self, *signals, status=DiscoverySourceStatus.SUCCESS):
        source = StaticSource("fixture", source_result(*signals, status=status))
        return discover_opportunity_hypotheses(request(), (source,), generated_at=NOW)

    def test_sin_fuentes_es_no_data_no_fallo_tecnico(self):
        result = discover_opportunity_hypotheses(request(), (), generated_at=NOW)
        self.assertIs(result.status, DiscoveryRunStatus.NO_DATA)
        self.assertFalse(result.hypotheses)

    def test_caso_0001_permanece_hold_sin_fuente_real(self):
        result = discover_opportunity_hypotheses(request(), (), generated_at=NOW)
        case_status = json.loads(CASE_STATUS.read_text(encoding="utf-8"))
        self.assertIs(result.status, DiscoveryRunStatus.NO_DATA)
        self.assertEqual(case_status["status"], "hold_evidence_acquisition")
        self.assertEqual(case_status["current_candidates"], [])
        self.assertEqual(case_status["capital"]["currently_authorized"]["amount"], "0.00")

    def test_no_data_y_fallo_tecnico_son_distintos(self):
        no_data = StaticSource("empty", DiscoverySourceResult("empty", DiscoverySourceStatus.NO_DATA, NOW, missing_information=("Sin observaciones.",)))
        broken = StaticSource("broken", object())
        first = discover_opportunity_hypotheses(request(), (no_data,), generated_at=NOW)
        second = discover_opportunity_hypotheses(request(), (broken,), generated_at=NOW)
        self.assertIs(first.status, DiscoveryRunStatus.NO_DATA)
        self.assertIs(second.status, DiscoveryRunStatus.TECHNICAL_FAILURE)

    def test_attention_no_se_convierte_en_demanda_ni_research_ready(self):
        result = self.run_with(signal(DiscoverySignalType.ATTENTION))
        hypothesis = result.hypotheses[0]
        self.assertIs(hypothesis.state, OpportunityHypothesisState.SURFACED)
        self.assertIn("attention", " ".join(hypothesis.to_dict()["why_surfaced"]))
        self.assertTrue(any(item.category is ResearchCategory.DEMAND for item in hypothesis.research_needs))

    def test_dos_senales_no_redundantes_con_presencia_es_research_ready(self):
        result = self.run_with(
            signal(DiscoverySignalType.CATALOG_PRESENCE),
            signal(DiscoverySignalType.ATTENTION),
        )
        self.assertIs(result.hypotheses[0].state, OpportunityHypothesisState.RESEARCH_READY)
        self.assertIs(result.status, DiscoveryRunStatus.HOLD_EVIDENCE_ACQUISITION)

    def test_senales_duplicadas_se_deduplican(self):
        item = signal()
        result = self.run_with(item, item)
        self.assertEqual(len(result.hypotheses[0].signals), 1)

    def test_identidad_normalizada_deduplica_case_unicode_y_espacios(self):
        result = self.run_with(
            signal(identity="  SYNTHETIC   Desk Organizer "),
            signal(DiscoverySignalType.ATTENTION, identity="synthetic desk organizer"),
        )
        self.assertEqual(len(result.hypotheses), 1)

    def test_contradiccion_visible_no_se_oculta(self):
        result = self.run_with(signal(contradictions=("La categoría declarada contradice la identidad del catálogo.",)))
        hypothesis = result.hypotheses[0]
        self.assertIs(hypothesis.state, OpportunityHypothesisState.CONTRADICTED)
        self.assertTrue(hypothesis.contradictions)

    def test_evidencia_expirada_permanece_visible_y_marca_stale(self):
        item = signal(freshness=FreshnessStatus.EXPIRED)
        result = self.run_with(item)
        self.assertIs(result.hypotheses[0].state, OpportunityHypothesisState.STALE)
        self.assertEqual(result.hypotheses[0].signals, (item,))

    def test_unknowns_y_research_needs_explicitos(self):
        hypothesis = self.run_with(signal()).hypotheses[0]
        self.assertEqual(len(hypothesis.research_needs), 7)
        self.assertIn("proveedor, MOQ, lead time y términos", hypothesis.unknowns)
        self.assertTrue(all(item.blocking for item in hypothesis.research_needs))

    def test_contexto_caso_orienta_needs_sin_score_ni_eliminar(self):
        hypothesis = self.run_with(signal()).hypotheses[0]
        costs = next(item for item in hypothesis.research_needs if item.category is ResearchCategory.COSTS)
        self.assertTrue(any("USD 750" in item for item in costs.known_information))
        self.assertTrue(any("USD 0" in item for item in costs.known_information))
        self.assertTrue(any("Capital autorizado USD 0" in item for item in self.run_with(signal()).warnings))

    def test_multiples_hipotesis_orden_determinista_y_tope(self):
        identities = json.loads(FIXTURE.read_text(encoding="utf-8"))["products"]
        signals = tuple(signal(identity=value) for value in reversed(identities))
        first = self.run_with(*signals)
        second = self.run_with(*reversed(signals))
        self.assertEqual([x.hypothesis_id for x in first.hypotheses], [x.hypothesis_id for x in second.hypotheses])
        self.assertEqual(len(first.hypotheses), 3)

    def test_tres_hipotesis_fixture_nunca_cambian_caso_a_identified(self):
        identities = json.loads(FIXTURE.read_text(encoding="utf-8"))["products"]
        signals = []
        for identity in identities:
            signals.extend((signal(identity=identity), signal(DiscoverySignalType.ATTENTION, identity=identity)))
        result = self.run_with(*signals)
        self.assertEqual(len(result.hypotheses), 3)
        self.assertIs(result.status, DiscoveryRunStatus.HOLD_EVIDENCE_ACQUISITION)
        self.assertFalse(result.real_hypotheses)

    def test_tres_hipotesis_de_fuente_real_simulada_satisfacen_solo_contrato(self):
        identities = ("contract product a", "contract product b", "contract product c")
        signals = []
        for identity in identities:
            signals.extend((
                signal(identity=identity, source_kind=DiscoverySourceKind.REAL, source="Contract test double"),
                signal(DiscoverySignalType.ATTENTION, identity=identity, source_kind=DiscoverySourceKind.REAL, source="Second contract test double"),
            ))
        result = self.run_with(*signals)
        self.assertIs(result.status, DiscoveryRunStatus.HYPOTHESES_IDENTIFIED)
        self.assertEqual(len(result.real_hypotheses), 3)

    def test_serializacion_conserva_provenance_y_no_muta(self):
        result = self.run_with(signal())
        payload = result.to_dict()
        payload["hypotheses"][0]["unknowns"].append("mutación externa")
        self.assertNotIn("mutación externa", result.hypotheses[0].unknowns)
        self.assertEqual(result.hypotheses[0].to_dict()["source_provenance"], ["Synthetic discovery fixture"])
        self.assertEqual(payload["source_results"][0]["generated_at"], NOW.isoformat())


if __name__ == "__main__":
    unittest.main()
