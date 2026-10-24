from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib

from hypothesis import given, settings, strategies as st
import pytest

from omnigridx.domain import (
    AlternativeResult,
    AlternativeType,
    CapabilityStatus,
    FiniteNumber,
    Identifier,
    ManifestDecimal,
    NamedHash,
    NormalizedRecord,
    ResultMetric,
    RunManifest,
    Sha256Digest,
    Timestamp,
    Unit,
    VersionReference,
)


def _digest(value: str) -> Sha256Digest:
    return Sha256Digest(hashlib.sha256(value.encode()).hexdigest())


def _manifest(seed: int, interval_count: int, tolerance: Decimal) -> RunManifest:
    return RunManifest(
        identifier=Identifier(f"manifest-{seed}"),
        scenario_version_id=Identifier(f"scenario-{seed}"),
        created_at=Timestamp(datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=seed)),
        alternative_types=tuple(AlternativeType),
        ordered_interval_ids=tuple(
            Identifier(f"interval-{index}") for index in range(interval_count)
        ),
        input_hashes=tuple(
            NamedHash(f"input-{index}", _digest(f"{seed}:{index}"))
            for index in range(interval_count)
        ),
        source_record_ids=tuple(
            Identifier(f"source-{seed}-{index}") for index in range(interval_count)
        ),
        pack=VersionReference("massachusetts", f"2026.{seed}"),
        policy_snapshot=VersionReference("policy", f"{seed}"),
        tariff_configuration=VersionReference("tariff", f"{seed}"),
        calculation_code=VersionReference("omnigridx", "test-build"),
        dependencies=(
            VersionReference("scipy", "1.15.1"),
            VersionReference("python", "3.13"),
        ),
        solver=VersionReference("scipy-milp", "1.15.1"),
        solver_settings=(
            ManifestDecimal("time_limit", FiniteNumber(30), "s"),
            ManifestDecimal("random_seed", FiniteNumber(seed), "integer"),
        ),
        tolerances=(
            ManifestDecimal("energy_balance", FiniteNumber(Decimal("0.000001")), "kWh"),
            ManifestDecimal("optimized_output", FiniteNumber(tolerance), "kWh"),
        ),
        random_seed=seed,
        deployment_mode="demo-local",
        capability_mode=CapabilityStatus.HACKATHON_DEMO,
    )


def _normalized_inputs(
    manifest: RunManifest, values: tuple[Decimal, ...]
) -> tuple[NormalizedRecord, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        NormalizedRecord(
            identifier=Identifier(f"normalized-{manifest.random_seed}-{index}"),
            dataset_version_id=Identifier(f"dataset-{manifest.random_seed}"),
            record_key=f"record-{index}",
            source_locator=f"row:{index + 1}",
            timestamp=Timestamp(start + timedelta(minutes=15 * index)),
            value=FiniteNumber(value),
            canonical_unit=Unit.KILOWATT_HOUR,
        )
        for index, value in enumerate(values)
    )


def _alternative_results(
    manifest: RunManifest,
    outputs: tuple[Decimal, Decimal, Decimal],
    labels: tuple[str, ...],
) -> tuple[AlternativeResult, ...]:
    run_id = Identifier(f"run-{manifest.random_seed}")
    alternatives = (
        AlternativeType.EXISTING,
        AlternativeType.RULE_BASED,
        AlternativeType.OPTIMIZED,
    )
    return tuple(
        AlternativeResult(
            identifier=Identifier(f"result-{manifest.random_seed}-{alternative.value}"),
            run_id=run_id,
            alternative_type=alternative,
            schedule_id=Identifier(f"schedule-{manifest.random_seed}-{alternative.value}"),
            metrics=(
                ResultMetric("energy_output", FiniteNumber(output), "kWh"),
            ),
            objective_components=(
                (ResultMetric("objective", FiniteNumber(output), "kWh"),)
                if alternative is AlternativeType.OPTIMIZED
                else ()
            ),
            solver_outcome="optimal" if alternative is AlternativeType.OPTIMIZED else None,
            checker_report_id=Identifier(
                f"checker-{manifest.random_seed}-{alternative.value}"
            ),
            labels=labels,
            disclosures=("advisory screening",),
        )
        for alternative, output in zip(alternatives, outputs, strict=True)
    )


# Feature: omnigridx, Property 9: Deterministic run reproducibility
# **Validates: Requirements 1.3, 4.1, 4.2, 9.2, 9.3, 10.6**
@given(
    seed=st.integers(min_value=0, max_value=10_000),
    normalized_values=st.lists(
        st.decimals(
            min_value=Decimal("0"),
            max_value=Decimal("1000000"),
            places=3,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=1,
        max_size=6,
    ),
    outputs=st.tuples(
        *(
            st.decimals(
                min_value=Decimal("-1000000"),
                max_value=Decimal("1000000"),
                places=3,
                allow_nan=False,
                allow_infinity=False,
            )
            for _ in AlternativeType
        )
    ),
    labels=st.lists(
        st.sampled_from(("Screening_Estimate", "Hackathon_Demo", "advisory")),
        min_size=1,
        max_size=3,
        unique=True,
    ),
    tolerance_microunits=st.integers(min_value=1, max_value=10_000),
    drift_percent=st.integers(min_value=-100, max_value=100),
)
@settings(max_examples=100, deadline=None)
def test_deterministic_run_reproducibility(
    seed: int,
    normalized_values: list[Decimal],
    outputs: tuple[Decimal, Decimal, Decimal],
    labels: list[str],
    tolerance_microunits: int,
    drift_percent: int,
) -> None:
    tolerance = Decimal(tolerance_microunits) / Decimal("1000000")
    manifest = _manifest(seed, len(normalized_values), tolerance)
    reordered_manifest = replace(
        manifest,
        input_hashes=tuple(reversed(manifest.input_hashes)),
        source_record_ids=tuple(reversed(manifest.source_record_ids)),
        dependencies=tuple(reversed(manifest.dependencies)),
        solver_settings=tuple(reversed(manifest.solver_settings)),
        tolerances=tuple(reversed(manifest.tolerances)),
    )

    with pytest.raises(FrozenInstanceError):
        manifest.random_seed = seed + 1  # type: ignore[misc]

    assert reordered_manifest.canonical_json() == manifest.canonical_json()
    assert reordered_manifest.fingerprint == manifest.fingerprint
    assert _normalized_inputs(manifest, tuple(normalized_values)) == _normalized_inputs(
        reordered_manifest, tuple(normalized_values)
    )

    expected = _alternative_results(manifest, outputs, tuple(labels))
    optimized_drift = tolerance * Decimal(drift_percent) / Decimal(100)
    replayed = _alternative_results(
        reordered_manifest,
        (outputs[0], outputs[1], outputs[2] + optimized_drift),
        tuple(labels),
    )

    assert tuple(result.alternative_type for result in replayed) == manifest.alternative_types
    assert tuple(result.labels for result in replayed) == tuple(
        result.labels for result in expected
    )
    assert replayed[:2] == expected[:2]

    for expected_metric, replayed_metric in zip(
        expected[2].metrics + expected[2].objective_components,
        replayed[2].metrics + replayed[2].objective_components,
        strict=True,
    ):
        assert expected_metric.value is not None
        assert replayed_metric.value is not None
        assert abs(expected_metric.value.value - replayed_metric.value.value) <= tolerance
