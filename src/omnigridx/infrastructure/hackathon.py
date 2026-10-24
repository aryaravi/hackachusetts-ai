"""Pinned public context and simulated human approval for the hackathon demo."""

from dataclasses import dataclass, field
import hashlib
from importlib.resources import files
import json
from typing import Any, cast
from urllib.parse import urlparse

from omnigridx.application.reporting import JudgeReport

OFFICIAL_DATA_PATH = "data/hackathon/official-data-v1.json"
APPROVAL_ORDER = (
    "analyst",
    "energy_provider_representative",
    "government_reviewer",
    "manager",
)
_ALLOWED_SOURCE_HOSTS = frozenset({"www.eia.gov", "www.iso-ne.com", "www.mass.gov"})
_ROLE_DETAILS = {
    "analyst": (
        "Internal energy analyst",
        "Validates calculations, units, caveats, and source-to-claim traceability.",
        "Avery Chen (synthetic)",
    ),
    "energy_provider_representative": (
        "Energy-provider representative",
        "Attests only the ISO and provider-context evidence used by the draft.",
        "Jordan Brooks (synthetic)",
    ),
    "government_reviewer": (
        "Government-data reviewer",
        "Attests only the interpretation of linked government data and policy records.",
        "Morgan Ellis (synthetic)",
    ),
    "manager": (
        "Internal manager",
        "Completes simulated financial and operational authorization after all reviews.",
        "Riley Shah (synthetic)",
    ),
}


class ApprovalConflict(ValueError):
    """A well-formed simulated approval that violates the required order."""


def _object_list(value: Any, field_name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{field_name} must be a nonempty object list")
    return cast(list[dict[str, Any]], value)


def load_official_data() -> tuple[dict[str, Any], str]:
    """Load and validate the immutable, manually curated official-source snapshot."""
    raw = files("omnigridx.infrastructure").joinpath(OFFICIAL_DATA_PATH).read_bytes()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("official data snapshot must be an object")
    document = cast(dict[str, Any], parsed)
    if document.get("schema_version") != "official-energy-snapshot-demo/1.0":
        raise ValueError("unsupported official data snapshot schema")
    if document.get("review_status") != "pending_human_validation":
        raise ValueError("official data snapshot must remain pending human validation")

    sources = _object_list(document.get("sources"), "sources")
    source_ids: set[str] = set()
    for source in sources:
        source_required = ("id", "publisher", "publisher_type", "title", "url", "reference_period", "limitation")
        if any(not isinstance(source.get(name), str) or not source[name].strip() for name in source_required):
            raise ValueError("every source requires complete textual provenance")
        source_id = cast(str, source["id"])
        if source_id in source_ids:
            raise ValueError("source IDs must be unique")
        source_ids.add(source_id)
        parsed_url = urlparse(cast(str, source["url"]))
        if parsed_url.scheme != "https" or parsed_url.hostname not in _ALLOWED_SOURCE_HOSTS:
            raise ValueError("source URL is not an allowlisted official HTTPS publisher")

    metrics = _object_list(document.get("metrics"), "metrics")
    metric_ids: set[str] = set()
    for metric in metrics:
        metric_required = ("id", "label", "value", "unit", "period", "kind", "source_id", "limitation")
        if any(not isinstance(metric.get(name), str) or not metric[name].strip() for name in metric_required):
            raise ValueError("every metric requires a value, unit, period, source, and limitation")
        metric_id = cast(str, metric["id"])
        if metric_id in metric_ids:
            raise ValueError("metric IDs must be unique")
        metric_ids.add(metric_id)
        if metric["source_id"] not in source_ids:
            raise ValueError("metric references an unknown source")

    options = _object_list(document.get("clean_options"), "clean_options")
    option_ids: set[str] = set()
    for option in options:
        option_required = ("id", "name", "category", "contribution", "evidence", "limitation")
        if any(not isinstance(option.get(name), str) or not option[name].strip() for name in option_required):
            raise ValueError("every clean option requires complete explanatory text")
        option_id = cast(str, option["id"])
        if option_id in option_ids:
            raise ValueError("clean option IDs must be unique")
        option_ids.add(option_id)
        option_sources = option.get("source_ids")
        if (
            not isinstance(option_sources, list)
            or not option_sources
            or any(not isinstance(source_id, str) or source_id not in source_ids for source_id in option_sources)
        ):
            raise ValueError("clean option references an unknown source")

    return document, hashlib.sha256(raw).hexdigest()


def build_simulated_ai_draft(
    report: JudgeReport,
    official_data: dict[str, Any],
    snapshot_fingerprint: str,
) -> dict[str, Any]:
    """Build a deterministic narrative sidecar without calling an AI service."""
    metrics = {
        cast(str, item["id"]): item
        for item in _object_list(official_data.get("metrics"), "metrics")
    }
    report_document = report.to_dict()
    alternatives = cast(list[dict[str, Any]], report_document["alternatives"])
    optimized = next(item for item in alternatives if item["alternative"] == "optimized")
    optimized_metrics = cast(dict[str, Any], optimized["metrics"])

    draft: dict[str, Any] = {
        "id": "simulated-ai-grid-review-v1",
        "label": "Simulated_AI_Draft",
        "status": "pending_human_review",
        "title": "Massachusetts clean-peak and resilience review",
        "generator": {
            "kind": "deterministic_template_simulation",
            "model_called": False,
            "disclosure": "No AI model or external service was called; this simulates an AI-drafted report for workflow demonstration.",
        },
        "source_report_fingerprint": report.fingerprint,
        "source_snapshot_fingerprint": snapshot_fingerprint,
        "summary": "Official context points to rising regional electricity use and a diverse resource pipeline. The checked site sample shows how clean generation and storage can be compared without turning contextual public data into a customer-specific recommendation.",
        "findings": [
            {
                "text": f"ISO New England projects {metrics['regional-energy-growth']['value']}{metrics['regional-energy-growth']['unit']} growth in annual electricity use for {metrics['regional-energy-growth']['period']}.",
                "evidence_ids": ["regional-energy-growth"],
            },
            {
                "text": f"Massachusetts reports {metrics['ma-storage-installed']['value']} {metrics['ma-storage-installed']['unit']} installed by {metrics['ma-storage-installed']['period']} and {metrics['ma-storage-pipeline']['value']} {metrics['ma-storage-pipeline']['unit']} in a separate pipeline.",
                "evidence_ids": ["ma-storage-installed", "ma-storage-pipeline"],
            },
            {
                "text": f"The optimized synthetic site schedule reports maximum import of {optimized_metrics['peak_import']['value']} {optimized_metrics['peak_import']['unit']} and critical service of {float(optimized_metrics['critical_service_fraction']) * 100:.0f}%.",
                "evidence_ids": ["fast-judge-optimized-schedule"],
            },
        ],
        "proposed_action": {
            "name": "Simulated clean-peak pilot review",
            "financial_scope": "Fictional planning envelope up to USD 25,000; no funds can be committed.",
            "operational_scope": "Stage the checked sample schedule for a tabletop exercise only; no command or control signal is produced.",
            "required_approvals": list(APPROVAL_ORDER),
            "effect": "Demonstration state only; no legal, financial, regulatory, procurement, or operational authority.",
        },
        "limitations": [
            "Pinned public facts have not been independently approved by the simulated reviewers.",
            "Queue, pipeline, target, forecast, historical, and site-screening values are not additive.",
            "No customer data, verified tariff, live grid feed, weather model, or site feasibility study is used.",
            "The draft cannot spend funds, file with a regulator, or operate equipment.",
        ],
    }
    canonical = json.dumps(draft, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    draft["fingerprint"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return draft


@dataclass(slots=True)
class ApprovalFlow:
    """Ordered, process-local acknowledgements with no real authorization effect."""

    completed_roles: list[str] = field(default_factory=list)

    @property
    def next_role(self) -> str | None:
        return None if len(self.completed_roles) == len(APPROVAL_ORDER) else APPROVAL_ORDER[len(self.completed_roles)]

    def approve(self, role: str) -> None:
        if role not in APPROVAL_ORDER:
            raise ValueError("unknown simulated approval role")
        expected = self.next_role
        if expected is None:
            raise ApprovalConflict("simulated approval flow is already complete")
        if role != expected:
            raise ApprovalConflict(f"{expected} must approve next")
        self.completed_roles.append(role)

    def reset(self) -> None:
        self.completed_roles.clear()

    def to_dict(self) -> dict[str, Any]:
        next_role = self.next_role
        return {
            "status": "simulated_authorization_complete" if next_role is None else "pending_simulated_approval",
            "completed_roles": list(self.completed_roles),
            "next_role": next_role,
            "progress": f"{len(self.completed_roles)}/{len(APPROVAL_ORDER)}",
            "roles": [
                {
                    "id": role,
                    "label": _ROLE_DETAILS[role][0],
                    "scope": _ROLE_DETAILS[role][1],
                    "actor": _ROLE_DETAILS[role][2],
                    "status": "approved" if role in self.completed_roles else ("ready" if role == next_role else "waiting"),
                }
                for role in APPROVAL_ORDER
            ],
            "authorization_effect": "Simulation only. No identity was verified and no financial or operational action is authorized.",
            "storage": "Shared in one process and cleared on restart or redeploy.",
        }
