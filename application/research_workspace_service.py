"""Workspace trazable para documentar investigación sin inventar verificación."""

from copy import deepcopy
from datetime import date, datetime, time, timezone
import hashlib
import json
from urllib.parse import urlparse, parse_qsl

from domain.value_objects.sensitive_data import contains_sensitive_reference


WORKSPACE_VERSION = "oriva-research-workspace/1.0"
CATEGORIES = {
    "demand": {"label": "Demanda", "blocking": True},
    "supplier": {"label": "Proveedor", "blocking": True},
    "costs": {"label": "Costos finales", "blocking": True},
    "restrictions": {"label": "Restricciones", "blocking": True},
    "competition": {"label": "Competencia observable", "blocking": True},
    "marketplace": {"label": "Condiciones del marketplace", "blocking": False},
    "logistics": {"label": "Logística", "blocking": False},
}
EVIDENCE_TYPES = {"data", "estimate", "assumption"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
MAX_IMPORT_BYTES = 1_000_000
_SENSITIVE_QUERY_KEYS = {
    "access_token", "api_key", "apikey", "client_secret", "password", "secret", "token"
}


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _text(value, field, *, required=True, maximum=1000):
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        if required:
            raise ValueError(f"{field} es obligatorio.")
        return None
    normalized = " ".join(value.split())
    if len(normalized) > maximum:
        raise ValueError(f"{field} supera el máximo de {maximum} caracteres.")
    return normalized


def _aware(value, field):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} debe incluir zona horaria.")
    return value


def _date_to_aware(value, field, *, end_of_day=False):
    if value is None:
        return None
    if isinstance(value, datetime):
        return _aware(value, field)
    if not isinstance(value, date):
        raise ValueError(f"{field} debe ser una fecha válida.")
    selected_time = time.max if end_of_day else time.min
    return datetime.combine(value, selected_time, timezone.utc)


def _safe_reference(value, *, required):
    reference = _text(value, "La referencia de la fuente", required=required, maximum=2000)
    if reference is None:
        return None
    parsed = urlparse(reference)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("La referencia debe ser una URL http/https válida.")
    if parsed.username or parsed.password:
        raise ValueError("La referencia no puede contener credenciales.")
    query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if query_keys & _SENSITIVE_QUERY_KEYS:
        raise ValueError("La referencia no puede contener secretos o tokens.")
    lowered = reference.casefold()
    if (
        any(f"{key}=" in lowered for key in _SENSITIVE_QUERY_KEYS)
        or contains_sensitive_reference(reference)
    ):
        raise ValueError("La referencia no puede contener secretos o tokens.")
    return reference


def _seed_evidence(dossier):
    market = dossier["market"]
    return [
        {
            "evidence_id": f"system-ebay-{dossier['dossier_id'][:16]}",
            "category": "competition",
            "summary": (
                f"eBay devolvió {market['active_listings_observed']} listings activos; "
                f"{market['exact_gtin_matches']} confirmaron el GTIN."
            ),
            "evidence_type": "data",
            "source_name": "eBay Browse API",
            "source_reference": None,
            "observed_at": dossier["generated_at"],
            "valid_until": None,
            "freshness": "unknown",
            "confidence": market["price_confidence"],
            "source_reviewed_by_user": False,
            "origin": "system_observed",
            "limitations": (
                "Mide oferta activa observable; no ventas, demanda, saturación ni cuota de mercado.",
            ),
        },
        {
            "evidence_id": f"system-cost-{dossier['dossier_id'][:16]}",
            "category": "costs",
            "summary": "Existe un costo manual y supuestos financieros para modelar escenarios.",
            "evidence_type": "assumption",
            "source_name": "Entrada declarada por el usuario",
            "source_reference": None,
            "observed_at": dossier["generated_at"],
            "valid_until": None,
            "freshness": "unknown",
            "confidence": "low",
            "source_reviewed_by_user": False,
            "origin": "system_derived",
            "limitations": (
                "No es una cotización de proveedor ni una tarifa oficial verificada.",
            ),
        },
        {
            "evidence_id": f"system-market-{dossier['dossier_id'][:16]}",
            "category": "marketplace",
            "summary": "El producto fue observado en el marketplace eBay US.",
            "evidence_type": "data",
            "source_name": "eBay Browse API",
            "source_reference": None,
            "observed_at": dossier["generated_at"],
            "valid_until": None,
            "freshness": "unknown",
            "confidence": "medium",
            "source_reviewed_by_user": False,
            "origin": "system_observed",
            "limitations": (
                "La presencia de listings no confirma elegibilidad del vendedor ni restricciones aplicables.",
            ),
        },
    ]


def crear_research_workspace(dossier, *, created_at=None):
    if not isinstance(dossier, dict) or not dossier.get("dossier_id"):
        raise ValueError("Se requiere un expediente de oportunidad válido.")
    created_at = _aware(created_at or datetime.now(timezone.utc), "created_at")
    workspace_id = hashlib.sha256(
        f"{WORKSPACE_VERSION}:{dossier['dossier_id']}".encode("utf-8")
    ).hexdigest()
    workspace = {
        "workspace_id": workspace_id,
        "version": WORKSPACE_VERSION,
        "dossier_id": dossier["dossier_id"],
        "product_gtin": dossier["product"]["gtin"],
        "created_at": created_at.isoformat(),
        "updated_at": created_at.isoformat(),
        "evidence": _seed_evidence(dossier),
        "warnings": [
            "La evidencia añadida manualmente representa una declaración del usuario; Oriva no la verifica automáticamente.",
            "El Workspace apoya investigación y revisión; nunca autoriza comprar inventario ni invertir.",
        ],
    }
    return evaluar_research_workspace(workspace, assessed_at=created_at)


def crear_evidencia_manual(
    *, category, summary, evidence_type, source_name=None, source_reference=None,
    observed_at, valid_until=None, confidence="low", source_reviewed_by_user=False,
    limitations=(), created_at=None,
):
    if category not in CATEGORIES:
        raise ValueError("La categoría de investigación es inválida.")
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError("El tipo de evidencia es inválido.")
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError("El nivel de confianza es inválido.")
    if not isinstance(source_reviewed_by_user, bool):
        raise ValueError("La revisión de la fuente debe ser booleana.")
    summary = _text(summary, "El resumen", maximum=1500)
    requires_source = evidence_type == "data"
    source_name = _text(source_name, "El nombre de la fuente", required=requires_source, maximum=200)
    source_reference = _safe_reference(source_reference, required=requires_source)
    observed_at = _date_to_aware(observed_at, "observed_at")
    valid_until = _date_to_aware(valid_until, "valid_until", end_of_day=True)
    if valid_until and valid_until < observed_at:
        raise ValueError("La vigencia no puede terminar antes de la fecha observada.")
    if source_reviewed_by_user and evidence_type != "data":
        raise ValueError("Solo un dato documentado puede marcarse como fuente revisada.")
    limitations = tuple(
        _text(item, "Cada limitación", maximum=500)
        for item in limitations
        if str(item).strip()
    )
    created_at = _aware(created_at or datetime.now(timezone.utc), "created_at")
    if observed_at > created_at:
        raise ValueError("La fecha observada no puede estar en el futuro.")
    semantic = {
        "category": category,
        "summary": summary,
        "evidence_type": evidence_type,
        "source_name": source_name,
        "source_reference": source_reference,
        "observed_at": observed_at.isoformat(),
        "valid_until": valid_until.isoformat() if valid_until else None,
        "confidence": confidence,
        "source_reviewed_by_user": source_reviewed_by_user,
        "limitations": limitations,
    }
    evidence_id = hashlib.sha256(_canonical(semantic).encode("utf-8")).hexdigest()
    return {
        "evidence_id": evidence_id,
        **semantic,
        "freshness": "unknown",
        "origin": "user_declared",
        "created_at": created_at.isoformat(),
        "limitations": limitations,
    }


def agregar_evidencia(workspace, evidence, *, updated_at=None):
    if not isinstance(workspace, dict) or not workspace.get("workspace_id"):
        raise ValueError("El Workspace es inválido.")
    if not isinstance(evidence, dict) or not evidence.get("evidence_id"):
        raise ValueError("La evidencia es inválida.")
    result = deepcopy(workspace)
    if any(item["evidence_id"] == evidence["evidence_id"] for item in result["evidence"]):
        return evaluar_research_workspace(result, assessed_at=updated_at)
    result["evidence"].append(deepcopy(evidence))
    return evaluar_research_workspace(result, assessed_at=updated_at)


def eliminar_evidencia_manual(workspace, evidence_id, *, updated_at=None):
    result = deepcopy(workspace)
    matches = [item for item in result.get("evidence", []) if item["evidence_id"] == evidence_id]
    if not matches:
        raise ValueError("No se encontró la evidencia indicada.")
    if matches[0].get("origin") != "user_declared":
        raise ValueError("La evidencia del sistema no puede eliminarse desde el Workspace.")
    result["evidence"] = [item for item in result["evidence"] if item["evidence_id"] != evidence_id]
    return evaluar_research_workspace(result, assessed_at=updated_at)


def _freshness(evidence, now):
    valid_until = evidence.get("valid_until")
    if not valid_until:
        return "unknown"
    expires = datetime.fromisoformat(valid_until)
    return "expired" if expires < now else "current"


def evaluar_research_workspace(workspace, *, assessed_at=None):
    assessed_at = _aware(assessed_at or datetime.now(timezone.utc), "assessed_at")
    result = deepcopy(workspace)
    for evidence in result.get("evidence", []):
        evidence["freshness"] = _freshness(evidence, assessed_at)

    coverage = []
    for category, definition in CATEGORIES.items():
        items = [item for item in result["evidence"] if item["category"] == category]
        documented = [
            item for item in items
            if item["evidence_type"] == "data"
            and item.get("source_reviewed_by_user")
            and item.get("source_reference")
            and item["freshness"] == "current"
        ]
        stale = [item for item in items if item["freshness"] == "expired"]
        if documented:
            status = "documented"
            explanation = "Existe una fuente actual que el usuario declaró haber revisado."
        elif stale:
            status = "stale"
            explanation = "Existe información vencida; permanece visible y necesita actualización."
        elif items:
            status = "partial"
            explanation = "Hay señales o supuestos, pero todavía no existe documentación actual revisada."
        else:
            status = "missing"
            explanation = "Todavía no se añadió evidencia para esta categoría."
        coverage.append({
            "category": category,
            "label": definition["label"],
            "blocking": definition["blocking"],
            "status": status,
            "explanation": explanation,
            "evidence_ids": tuple(item["evidence_id"] for item in items),
        })

    blocking = [item for item in coverage if item["blocking"]]
    if any(item["status"] == "stale" for item in blocking):
        state = "needs_refresh"
    elif all(item["status"] == "documented" for item in blocking):
        state = "documented_for_review"
    else:
        state = "collecting_evidence"
    result["coverage"] = coverage
    result["status"] = state
    result["documented_for_decision_review"] = state == "documented_for_review"
    result["purchase_authorized"] = False
    result["missing_blocking_categories"] = tuple(
        item["category"] for item in blocking if item["status"] != "documented"
    )
    result["updated_at"] = assessed_at.isoformat()
    return result


def exportar_workspace_json(workspace):
    if not isinstance(workspace, dict) or not workspace.get("workspace_id"):
        raise ValueError("El Workspace es inválido.")
    return {
        "nombre_archivo": f"oriva_research_{workspace['product_gtin']}.json",
        "contenido": (_canonical(workspace) + "\n").encode("utf-8"),
        "mime": "application/json",
    }


def exportar_workspace_txt(workspace):
    if not isinstance(workspace, dict) or not workspace.get("workspace_id"):
        raise ValueError("El Workspace es inválido.")
    status_labels = {
        "missing": "Faltante",
        "partial": "Parcial",
        "documented": "Documentado por el usuario",
        "stale": "Vencido",
    }
    lines = [
        "ORIVA — RESEARCH WORKSPACE",
        "=" * 40,
        f"Workspace: {workspace['workspace_id']}",
        f"GTIN: {workspace['product_gtin']}",
        f"Actualizado: {workspace['updated_at']}",
        f"Estado: {workspace['status']}",
        "",
        "COBERTURA",
    ]
    for item in workspace["coverage"]:
        lines.append(
            f"- {item['label']}: {status_labels[item['status']]} — {item['explanation']}"
        )
    lines.extend(("", "EVIDENCIA"))
    for item in workspace["evidence"]:
        lines.extend((
            f"- [{item['category']}] {item['summary']}",
            f"  Tipo: {item['evidence_type']} | Fuente: {item.get('source_name') or 'No declarada'}",
            f"  Vigencia: {item['freshness']} | Confianza: {item['confidence']}",
        ))
    lines.extend((
        "",
        "ADVERTENCIAS",
        *(f"- {warning}" for warning in workspace["warnings"]),
        "",
        "La revisión humana sigue siendo obligatoria.",
        "Este Workspace no autoriza comprar inventario ni invertir.",
    ))
    return {
        "nombre_archivo": f"oriva_research_{workspace['product_gtin']}.txt",
        "contenido": "\n".join(lines).encode("utf-8"),
        "mime": "text/plain",
    }


def importar_workspace_json(content, base_workspace, *, imported_at=None):
    """Restaura evidencia manual; nunca confía en evidencia de sistema importada."""
    if not isinstance(base_workspace, dict) or not base_workspace.get("workspace_id"):
        raise ValueError("El Workspace base es inválido.")
    if isinstance(content, str):
        content = content.encode("utf-8")
    if not isinstance(content, bytes) or not content or len(content) > MAX_IMPORT_BYTES:
        raise ValueError("El archivo de investigación es inválido o demasiado grande.")
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("El archivo de investigación no contiene JSON válido.") from None
    if not isinstance(payload, dict) or payload.get("version") != WORKSPACE_VERSION:
        raise ValueError("La versión del archivo de investigación no es compatible.")
    if payload.get("dossier_id") != base_workspace.get("dossier_id"):
        raise ValueError("El archivo pertenece a otro expediente de oportunidad.")
    evidence_items = payload.get("evidence")
    if not isinstance(evidence_items, list) or len(evidence_items) > 200:
        raise ValueError("El registro de evidencia importado es inválido.")

    imported_at = _aware(imported_at or datetime.now(timezone.utc), "imported_at")
    result = deepcopy(base_workspace)
    known_ids = {item["evidence_id"] for item in result["evidence"]}
    for item in evidence_items:
        if not isinstance(item, dict) or item.get("origin") != "user_declared":
            continue
        try:
            observed_at = datetime.fromisoformat(item["observed_at"])
            valid_until = (
                datetime.fromisoformat(item["valid_until"])
                if item.get("valid_until") else None
            )
            created_at = (
                datetime.fromisoformat(item["created_at"])
                if item.get("created_at") else imported_at
            )
        except (KeyError, TypeError, ValueError):
            raise ValueError("Una evidencia importada contiene fechas inválidas.") from None
        rebuilt = crear_evidencia_manual(
            category=item.get("category"),
            summary=item.get("summary"),
            evidence_type=item.get("evidence_type"),
            source_name=item.get("source_name"),
            source_reference=item.get("source_reference"),
            observed_at=observed_at,
            valid_until=valid_until,
            confidence=item.get("confidence"),
            source_reviewed_by_user=item.get("source_reviewed_by_user"),
            limitations=tuple(item.get("limitations") or ()),
            created_at=created_at,
        )
        if rebuilt["evidence_id"] != item.get("evidence_id"):
            raise ValueError("Una evidencia importada fue modificada o está corrupta.")
        if rebuilt["evidence_id"] not in known_ids:
            result["evidence"].append(rebuilt)
            known_ids.add(rebuilt["evidence_id"])
    return evaluar_research_workspace(result, assessed_at=imported_at)
