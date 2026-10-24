import json

from omnigridx.application import REPORT_ASSUMPTIONS, REPORT_DISCLOSURES, REPORT_EXCLUSIONS
from omnigridx.infrastructure.sample import build_sample_report
from omnigridx.web.presentation import ReportPresenter


EXPECTED_TOP_LEVEL_KEYS = {
    "alternatives",
    "assumptions",
    "disclosures",
    "exclusions",
    "label",
    "manifest",
    "recommendation",
    "report_fingerprint",
    "sample_id",
    "schema_version",
}
EXPECTED_METRIC_KEYS = {
    "clean_energy_share",
    "critical_service_fraction",
    "operating_cost",
    "outage_service",
    "peak_import",
    "purchased_electricity_emissions",
}
FORBIDDEN_AFFIRMATIVE_CLAIMS = (
    "AI-powered",
    "Optimization uses AI",
    "Customer-specific result",
    "This is a verified tariff",
    "This is a historical bill reconciliation",
    "This is probabilistic reliability analysis",
    "Local-grid feasibility is evaluated",
    "Weather forecasting is included",
    "Demand forecasting is included",
)


def test_json_export_preserves_v1_schema_and_is_byte_stable() -> None:
    report = build_sample_report("demo-local")
    presenter = ReportPresenter()

    exported = presenter.render_json(report)
    document = json.loads(exported)

    assert exported == report.to_json() == presenter.render_json(report)
    assert set(document) == EXPECTED_TOP_LEVEL_KEYS
    assert document["schema_version"] == "fast-judge-mvp-v1"
    assert document["sample_id"] == report.sample_id
    assert document["manifest"]["fingerprint"] == str(report.comparison.manifest.fingerprint)
    assert document["report_fingerprint"] == report.fingerprint
    assert [item["alternative"] for item in document["alternatives"]] == [
        "existing",
        "rule_based",
        "optimized",
    ]
    assert all(set(item["metrics"]) == EXPECTED_METRIC_KEYS for item in document["alternatives"])
    assert all(item["independent_checker"]["status"] == "passed" for item in document["alternatives"])
    assert [item["solver"]["status"] for item in document["alternatives"]] == [
        "not_applicable",
        "not_applicable",
        "optimal",
    ]
    assert document["assumptions"] == list(REPORT_ASSUMPTIONS)
    assert document["exclusions"] == list(REPORT_EXCLUSIONS)
    assert document["disclosures"] == list(REPORT_DISCLOSURES)


def test_human_export_is_standalone_deterministic_and_complete() -> None:
    report = build_sample_report("demo-local")
    presenter = ReportPresenter()
    document = report.to_dict()

    exported = presenter.render_html(report)

    assert exported == presenter.render_html(report)
    assert exported.startswith("<!doctype html>")
    for expected in (
        report.sample_id,
        str(report.comparison.manifest.identifier),
        str(report.comparison.manifest.fingerprint),
        report.fingerprint,
        "Existing operation",
        "Solar-first rule",
        "Optimized dispatch",
        "Solver status: optimal",
        "Outage_Service_Screening",
        "Screening_Estimate",
        *REPORT_ASSUMPTIONS,
        *REPORT_EXCLUSIONS,
        *REPORT_DISCLOSURES,
    ):
        assert expected in exported
    for alternative in document["alternatives"]:
        assert alternative["schedule"]["id"] in exported
        assert alternative["metrics"]["operating_cost"]["amount"]["value"] in exported
        assert alternative["metrics"]["peak_import"]["value"] in exported
        assert alternative["metrics"]["outage_service"]["status"] in exported
        assert alternative["metrics"]["purchased_electricity_emissions"]["estimate"]["value"] in exported
        assert alternative["independent_checker"]["status"] in exported


def test_exports_exclude_exact_forbidden_affirmative_claims() -> None:
    report = build_sample_report("demo-local")
    presenter = ReportPresenter()
    exports = (presenter.render_json(report), presenter.render_html(report))

    for forbidden in FORBIDDEN_AFFIRMATIVE_CLAIMS:
        assert all(forbidden.casefold() not in exported.casefold() for exported in exports)
