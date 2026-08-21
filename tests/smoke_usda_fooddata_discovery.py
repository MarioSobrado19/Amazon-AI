"""Smoke real mínimo de USDA FoodData Central; no persiste la respuesta cruda."""

from datetime import datetime, timezone
import json

from application.discovery_models import DiscoveryRequest
from application.opportunity_discovery_service import discover_opportunity_hypotheses
from domain.value_objects import Region
from infrastructure.usda.fooddata_central_discovery_source import (
    UsdaFoodDataCentralDiscoverySource,
)


def main():
    now = datetime.now(timezone.utc)
    request = DiscoveryRequest(
        "oriva-case-0001-usda-smoke-v1",
        "oriva-case-0001-objective",
        now,
        Region("US"),
        750,
        0,
        90,
        5,
    )
    source = UsdaFoodDataCentralDiscoverySource("protein bar", hard_cap=5)
    result = discover_opportunity_hypotheses(request, (source,), generated_at=now)
    output = {
        "classification": "REAL USDA CATALOG DISCOVERY — NOT DEMAND, SALES OR PROFITABILITY",
        "query": "protein bar",
        "source_status": result.source_results[0].status.value,
        "source_error_code": result.source_results[0].error_code,
        "pipeline_status": result.status.value,
        "signals": [
            {
                "fdc_id": item.signals[0].value.to_dict()["fdc_id"],
                "description": item.signals[0].value.to_dict()["description"],
                "category": item.signals[0].value.to_dict()["category"],
                "state": item.state.value,
            }
            for item in result.hypotheses
        ],
        "research_ready": sum(item.state.value == "research_ready" for item in result.hypotheses),
        "current_candidates": [],
        "capital_authorized_usd": 0,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
