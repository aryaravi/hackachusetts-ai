from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json

import pytest

from omnigridx.domain import (
    AlternativeType,
    CapabilityStatus,
    Duration,
    Energy,
    FiniteNumber,
    Identifier,
    IntervalResult,
    ManifestDecimal,
    NamedHash,
    RunManifest,
    Schedule,
    Sha256Digest,
    Timestamp,
    Unit,
    VersionReference,
)


def manifest(*, interval_ids: tuple[str, ...] = ("i-1", "i-2")) -> RunManifest:
    version = VersionReference("pack", "2026.1")
    return RunManifest(
        identifier=Identifier("manifest-1"),
        scenario_version_id=Identifier("scenario-1"),
        created_at=Timestamp(datetime(2026, 2, 1, tzinfo=UTC)),
        alternative_types=(
            AlternativeType.EXISTING,
            AlternativeType.RULE_BASED,
            AlternativeType.OPTIMIZED,
        ),
        ordered_interval_ids=tuple(Identifier(value) for value in interval_ids),
        input_hashes=(NamedHash("load", Sha256Digest("a" * 64)),),
        source_record_ids=(Identifier("source-1"),),
        pack=version,
        policy_snapshot=VersionReference("policy", "1"),
        tariff_configuration=VersionReference("tariff", "1"),
        calculation_code=VersionReference("omnigridx", "abc123"),
        dependencies=(VersionReference("scipy", "1.15.1"),),
        solver=VersionReference("scipy-milp", "1.15.1"),
        solver_settings=(
            ManifestDecimal("time_limit", FiniteNumber(30), "s"),
        ),
        tolerances=(
            ManifestDecimal("energy_balance", FiniteNumber(Decimal("0.0000010")), "kWh"),
        ),
        random_seed=0,
        deployment_mode="demo-local",
        capability_mode=CapabilityStatus.HACKATHON_DEMO,
    )


def test_alternative_type_has_exactly_the_three_release_alternatives() -> None:
    assert tuple(AlternativeType) == (
        AlternativeType.EXISTING,
        AlternativeType.RULE_BASED,
        AlternativeType.OPTIMIZED,
    )


def test_manifest_is_immutable_and_rejects_an_incomplete_alternative_set() -> None:
    value = manifest()
    with pytest.raises(FrozenInstanceError):
        value.random_seed = 1  # type: ignore[misc]

    with pytest.raises(ValueError, match="exactly existing"):
        replace(value, alternative_types=(AlternativeType.EXISTING,))


def test_manifest_serialization_is_canonical_and_fingerprinted() -> None:
    value = manifest()
    payload = json.loads(value.canonical_json())

    assert payload["ordered_interval_ids"] == ["i-1", "i-2"]
    assert payload["tolerances"] == [
        {"name": "energy_balance", "unit": "kWh", "value": "0.000001"}
    ]
    assert payload["random_seed"] == "0"
    assert payload["created_at_utc"] == "2026-02-01T00:00:00Z"
    assert value.canonical_json() == value.canonical_json()
    assert str(value.fingerprint) == hashlib.sha256(
        value.canonical_json().encode("utf-8")
    ).hexdigest()


def test_manifest_fingerprint_preserves_interval_order() -> None:
    assert manifest(interval_ids=("i-1", "i-2")).fingerprint != manifest(
        interval_ids=("i-2", "i-1")
    ).fingerprint


def test_manifest_requires_valid_hashes_unique_intervals_and_explicit_units() -> None:
    with pytest.raises(ValueError, match="64 lowercase"):
        Sha256Digest("not-a-hash")
    with pytest.raises(ValueError, match="unique ordered"):
        manifest(interval_ids=("i-1", "i-1"))
    with pytest.raises(ValueError, match="explicit unit"):
        ManifestDecimal("gap", FiniteNumber(Decimal("0.01")), "")


def test_quantity_construction_used_by_records_keeps_explicit_units() -> None:
    duration = Duration(Decimal("0.25"), Unit.HOUR)
    assert (duration.value, duration.unit) == (Decimal("0.25"), Unit.HOUR)


def test_interval_result_has_every_required_energy_accounting_field() -> None:
    energy = Energy(0, Unit.KILOWATT_HOUR)
    result = IntervalResult(
        run_id=Identifier("run-1"),
        alternative_type=AlternativeType.EXISTING,
        interval_id=Identifier("i-1"),
        generation_available=energy,
        generation_dispatched=energy,
        generation_curtailed=energy,
        grid_import=energy,
        grid_export=energy,
        battery_charge=energy,
        battery_discharge=energy,
        served_critical_load=energy,
        served_noncritical_load=energy,
        critical_unserved_load=energy,
        noncritical_unserved_load=energy,
        other_conversion_loss=energy,
        storage_conversion_loss=energy,
        state_of_charge_start=energy,
        state_of_charge_end=energy,
        constraint_check_passed=True,
    )

    assert {field.name for field in fields(result)} == {
        "run_id",
        "alternative_type",
        "interval_id",
        "generation_available",
        "generation_dispatched",
        "generation_curtailed",
        "grid_import",
        "grid_export",
        "battery_charge",
        "battery_discharge",
        "served_critical_load",
        "served_noncritical_load",
        "critical_unserved_load",
        "noncritical_unserved_load",
        "other_conversion_loss",
        "storage_conversion_loss",
        "state_of_charge_start",
        "state_of_charge_end",
        "constraint_check_passed",
    }
    schedule = Schedule(
        Identifier("schedule-1"),
        Identifier("scenario-1"),
        AlternativeType.EXISTING,
        (result,),
    )
    assert schedule.intervals == (result,)
    with pytest.raises(ValueError, match="must match"):
        replace(schedule, alternative_type=AlternativeType.OPTIMIZED)
