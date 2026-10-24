from dataclasses import replace
import re

import pytest

from omnigridx.application import (
    JudgeReport,
    REPORT_ASSUMPTIONS,
    REPORT_DISCLOSURES,
    REPORT_EXCLUSIONS,
)
from omnigridx.infrastructure.sample import build_sample_report


def test_report_schema_snapshot_and_fingerprint() -> None:
    report = build_sample_report("demo-local")
    document = report.to_dict()
    first = document["alternatives"][0]
    snapshot = {
        "schema_version": document["schema_version"],
        "label": document["label"],
        "sample_id": document["sample_id"],
        "manifest": {
            "identifier": document["manifest"]["identifier"],
            "scenario_version_id": document["manifest"]["scenario_version_id"],
            "fingerprint": document["manifest"]["fingerprint"],
        },
        "alternative_names": [item["alternative"] for item in document["alternatives"]],
        "metric_keys": sorted(first["metrics"]),
        "rate_configuration": first["metrics"]["operating_cost"]["rate_configuration"],
        "emissions_factor": first["metrics"]["purchased_electricity_emissions"]["factor"],
        "recommendation": document["recommendation"],
        "assumptions": document["assumptions"],
        "exclusions": document["exclusions"],
        "disclosures": document["disclosures"],
    }

    assert snapshot == {
        "schema_version": "fast-judge-mvp-v1",
        "label": "Fast_Judge_MVP",
        "sample_id": "massachusetts-commercial-site-sample-v1",
        "manifest": {
            "identifier": "bundled-manifest-v1",
            "scenario_version_id": "bundled-sample-v1",
            "fingerprint": "3369a36aff781a8e4ea9e086f5965954132e4349d70fa7da15caaf191305cd88",
        },
        "alternative_names": ["existing", "rule_based", "optimized"],
        "metric_keys": [
            "clean_energy_share",
            "critical_service_fraction",
            "operating_cost",
            "outage_service",
            "peak_import",
            "purchased_electricity_emissions",
        ],
        "rate_configuration": {
            "currency": "USD",
            "effective_period": ["2026-01-01", "2026-12-31"],
            "exclusions": ["demand charges", "fixed charges", "taxes and riders"],
            "id": "bundled-ma-sample-screening-rate",
            "source_or_assumption": "Bundled sample assumption; not a utility tariff",
            "units": "USD/kWh",
            "version": "2026.1",
        },
        "emissions_factor": {
            "classification": "average sample assumption",
            "data_year": 2022,
            "geography": "ISO-NE sample",
            "included_gases": ["CO2", "CH4", "N2O"],
            "intended_purpose": "sample screening",
            "source": "Bundled synthetic screening assumption",
            "units": "kgCO2e/kWh",
            "value": "0.4",
            "version": "sample-v1",
        },
        "recommendation": None,
        "assumptions": list(REPORT_ASSUMPTIONS),
        "exclusions": list(REPORT_EXCLUSIONS),
        "disclosures": list(REPORT_DISCLOSURES),
    }
    assert len(document["alternatives"]) == 3
    assert all(sorted(item["metrics"]) == snapshot["metric_keys"] for item in document["alternatives"])
    assert document["report_fingerprint"] == "692f2d67cf31e8ecad9050f4486b615f0ce586078f78fb865ce8eaf1ded006f3"
    assert report.to_json() == build_sample_report("demo-local").to_json()


def test_report_has_exact_disclosures_without_forbidden_affirmative_claims() -> None:
    report = build_sample_report("demo-local")

    assert report.assumptions == REPORT_ASSUMPTIONS
    assert report.exclusions == REPORT_EXCLUSIONS
    assert report.disclosures == REPORT_DISCLOSURES
    text = report.to_json().casefold()
    forbidden_claims = (
        r"ai-powered",
        r"machine learning",
        r"optimization uses ai",
        r"customer-specific",
        r"(?<!no )(?<!not a )verified tariff",
        r"historically reconciled tariff",
        r"(?<!not )probabilistic reliability analysis",
        r"local-grid feasibility is evaluated",
        r"weather forecasting is included",
        r"demand forecasting is included",
    )
    assert not [claim for claim in forbidden_claims if re.search(claim, text)]


def test_report_rejects_incomplete_or_unchecked_comparisons() -> None:
    report = build_sample_report("demo-local")
    alternatives = report.comparison.alternatives

    with pytest.raises(ValueError, match="exactly three alternatives"):
        JudgeReport(
            report.sample_id,
            replace(report.comparison, alternatives=(alternatives[1], alternatives[0], alternatives[2])),
        )

    failed = replace(
        alternatives[0],
        checker_report=replace(alternatives[0].checker_report, checked_schedule=None),
    )
    with pytest.raises(ValueError, match="independently checked alternatives"):
        JudgeReport(
            report.sample_id,
            replace(report.comparison, alternatives=(failed, alternatives[1], alternatives[2])),
        )
