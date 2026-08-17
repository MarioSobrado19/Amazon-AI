"""Smoke real y manual; no forma parte de la suite determinista."""

from datetime import datetime, timedelta, timezone
import json

from application.research_models import ResearchCapabilityRequest, ResearchExecutionContext
from domain.enums import ResearchCategory
from infrastructure.wikimedia.demand_interest_capability import WikimediaPageviewsDemandCapability


if __name__ == "__main__":
    end = datetime.now(timezone.utc).date() - timedelta(days=2)
    start = end - timedelta(days=2)
    request = ResearchCapabilityRequest(
        "smoke-wikimedia-pageviews",
        ResearchCategory.DEMAND,
        "¿Cuántas vistas recibió este artículo de Wikipedia?",
        "wikipedia_article",
        "Headphones",
        ResearchExecutionContext("smoke-public", "smoke-wikimedia", datetime.now(timezone.utc)),
        time_scope=f"{start.isoformat()}/{end.isoformat()}",
    )
    result = WikimediaPageviewsDemandCapability().execute(request)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    raise SystemExit(0 if result.status.value == "success" else 1)
