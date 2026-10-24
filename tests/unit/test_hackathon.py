import pytest

from omnigridx.infrastructure.hackathon import (
    APPROVAL_ORDER,
    ApprovalConflict,
    ApprovalFlow,
    build_simulated_ai_draft,
    load_official_data,
)
from omnigridx.infrastructure.sample import build_sample_report


def test_official_snapshot_and_simulated_draft_are_traceable_and_stable() -> None:
    data, fingerprint = load_official_data()
    report = build_sample_report("demo-local")
    first = build_simulated_ai_draft(report, data, fingerprint)
    second = build_simulated_ai_draft(report, data, fingerprint)

    assert {source["publisher"] for source in data["sources"]} == {
        "ISO New England",
        "Commonwealth of Massachusetts",
        "U.S. Energy Information Administration",
    }
    assert len(data["metrics"]) == 14
    assert {option["id"] for option in data["clean_options"]} == {
        "solar",
        "wind",
        "hydro",
        "nuclear",
        "geothermal",
        "storage",
        "demand-flexibility",
        "efficiency",
    }
    assert len(fingerprint) == 64
    assert first == second
    assert first["source_report_fingerprint"] == report.fingerprint
    assert first["source_snapshot_fingerprint"] == fingerprint
    assert first["generator"]["model_called"] is False
    assert "no funds can be committed" in first["proposed_action"]["financial_scope"]
    assert "no command or control signal" in first["proposed_action"]["operational_scope"]


def test_simulated_approvals_are_ordered_fail_closed_and_resettable() -> None:
    flow = ApprovalFlow()

    with pytest.raises(ValueError, match="unknown"):
        flow.approve("ai_agent")
    with pytest.raises(ApprovalConflict, match="analyst"):
        flow.approve("manager")
    assert flow.completed_roles == []

    for index, role in enumerate(APPROVAL_ORDER):
        flow.approve(role)
        assert flow.completed_roles == list(APPROVAL_ORDER[: index + 1])
        if index == 0:
            with pytest.raises(ApprovalConflict, match="energy_provider_representative"):
                flow.approve("analyst")
            assert flow.completed_roles == ["analyst"]

    assert flow.next_role is None
    assert flow.to_dict()["status"] == "simulated_authorization_complete"
    assert "No identity was verified" in flow.to_dict()["authorization_effect"]
    with pytest.raises(ApprovalConflict, match="already complete"):
        flow.approve("manager")

    flow.reset()
    assert flow.to_dict()["next_role"] == "analyst"
    assert flow.completed_roles == []
