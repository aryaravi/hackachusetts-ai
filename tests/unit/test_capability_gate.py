import pytest

from omnigridx.application import (
    CapabilityGate,
    ConclusionKind,
    DataSourceKind,
    DemoLocalSettings,
    ReleaseCapability,
)
from omnigridx.domain import CapabilityStatus


@pytest.fixture
def gate() -> CapabilityGate:
    return CapabilityGate(frozenset({"sample-load", "sample-tariff"}))


@pytest.mark.parametrize("host", ["127.0.0.1", "127.1.2.3", "::1"])
def test_demo_local_starts_unauthenticated_only_with_safe_local_configuration(
    gate: CapabilityGate, host: str
) -> None:
    decision = gate.validate_demo_local_startup(
        DemoLocalSettings(host, ("sample-load", "sample-tariff"))
    )

    assert decision.allowed
    assert decision.reasons == ()


@pytest.mark.parametrize(
    ("settings", "reason"),
    [
        (DemoLocalSettings("0.0.0.0", ("sample-load",)), "loopback"),
        (DemoLocalSettings("localhost", ("sample-load",)), "loopback"),
        (DemoLocalSettings("127.0.0.1", ()), "at least one"),
        (DemoLocalSettings("127.0.0.1", ("other",)), "not bundled"),
        (DemoLocalSettings("127.0.0.1", ("sample-load",), uploads_enabled=True), "uploads"),
        (
            DemoLocalSettings("127.0.0.1", ("sample-load",), remote_adapters_enabled=True),
            "remote adapters",
        ),
        (
            DemoLocalSettings("127.0.0.1", ("sample-load",), customer_data_enabled=True),
            "customer data",
        ),
    ],
)
def test_demo_local_startup_fails_closed(
    gate: CapabilityGate, settings: DemoLocalSettings, reason: str
) -> None:
    decision = gate.validate_demo_local_startup(settings)

    assert not decision.allowed
    assert any(reason in diagnostic for diagnostic in decision.reasons)


def test_demo_local_data_admission_rejects_nonbundled_and_customer_data(
    gate: CapabilityGate,
) -> None:
    assert gate.admit_demo_local_data(
        "sample-load", DataSourceKind.BUNDLED_SAMPLE
    ).allowed
    assert not gate.admit_demo_local_data(
        "unknown", DataSourceKind.BUNDLED_SAMPLE
    ).allowed
    assert not gate.admit_demo_local_data(
        "sample-load", DataSourceKind.AUTHORIZED_CUSTOMER_DATA
    ).allowed


@pytest.mark.parametrize("conclusion", [ConclusionKind.SITE_LOAD, ConclusionKind.TARIFF])
def test_first_release_conclusions_require_recorded_customer_authorization(
    gate: CapabilityGate, conclusion: ConclusionKind
) -> None:
    assert gate.authorize_first_release_conclusion(
        DataSourceKind.AUTHORIZED_CUSTOMER_DATA,
        conclusion,
        authorization_recorded=True,
    ).allowed
    assert not gate.authorize_first_release_conclusion(
        DataSourceKind.AUTHORIZED_CUSTOMER_DATA,
        conclusion,
        authorization_recorded=False,
    ).allowed
    for source_kind in (DataSourceKind.PUBLIC, DataSourceKind.ZONAL):
        assert not gate.authorize_first_release_conclusion(
            source_kind, conclusion, authorization_recorded=True
        ).allowed
        assert gate.authorize_first_release_conclusion(
            source_kind, ConclusionKind.CONTEXT, authorization_recorded=False
        ).allowed


def test_out_of_scope_capabilities_have_explicit_demo_or_future_labels(
    gate: CapabilityGate,
) -> None:
    assert gate.capability_status(
        ReleaseCapability.BUNDLED_SAMPLE_SCREENING
    ) is CapabilityStatus.HACKATHON_DEMO
    assert gate.capability_status(
        ReleaseCapability.DATA_CENTER_LOAD_SAMPLE
    ) is CapabilityStatus.HACKATHON_DEMO
    for capability in (
        ReleaseCapability.LIVE_SOURCE_ADAPTERS,
        ReleaseCapability.OPERATIONAL_ML_FORECAST,
        ReleaseCapability.BROAD_POLICY_INTELLIGENCE,
        ReleaseCapability.BESPOKE_DATA_CENTER_THERMAL_MODELING,
    ):
        assert gate.capability_status(capability) is CapabilityStatus.FUTURE_CAPABILITY
