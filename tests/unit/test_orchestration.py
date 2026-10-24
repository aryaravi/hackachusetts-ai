from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from omnigridx.application import (
    BUNDLED_SAMPLE_RATE_CONFIGURATION,
    CleanEnergyAttribution,
    CostMinimizingOptimizer,
    EmissionsFactor,
    IntervalCostRate,
    OptimizationCosts,
    OptimizationStatus,
    OrchestrationError,
    OutageDeclaration,
    RunOrchestrator,
    ThreeAlternativeComparison,
)
from omnigridx.domain import (
    AlternativeType,
    BatterySpec,
    CapabilityStatus,
    ConstraintChecker,
    ConstraintReport,
    ConstraintTolerances,
    Duration,
    Energy,
    FiniteNumber,
    GridIntervalLimit,
    Identifier,
    Interval,
    IntervalDispatch,
    ManifestDecimal,
    NamedHash,
    Power,
    ReserveMode,
    RunManifest,
    Schedule,
    Sha256Digest,
    SimulationIntervalInput,
    SimulationRequest,
    TerminalTreatment,
    TerminalTreatmentKind,
    Timestamp,
    Unit,
    VersionReference,
)
from omnigridx.infrastructure import ScipyMilpSolver


def energy(value: str | int | Decimal) -> Energy:
    return Energy(Decimal(value), Unit.KILOWATT_HOUR)


def power(value: str | int) -> Power:
    return Power(Decimal(value), Unit.KILOWATT)


def checker() -> ConstraintChecker:
    tolerance = energy("0.000001")
    return ConstraintChecker(
        ConstraintTolerances("2026.1", tolerance, tolerance, tolerance, tolerance)
    )


def sample() -> tuple[RunManifest, SimulationRequest]:
    intervals = (
        SimulationIntervalInput(
            interval=Interval(
                Identifier("normal"),
                Timestamp(datetime(2026, 1, 1, 0, tzinfo=UTC)),
                Duration(1, Unit.HOUR),
            ),
            generation_available=energy(2),
            generation_asset_available=True,
            battery_available=True,
            critical_load=energy(1),
            noncritical_load=energy(0),
            grid=GridIntervalLimit(True, True, True, power(2), power(2)),
            dispatch=IntervalDispatch(
                energy(0), energy(1), energy(0), energy(0), energy(0),
                energy(0), energy(0), energy(0),
            ),
        ),
        SimulationIntervalInput(
            interval=Interval(
                Identifier("outage"),
                Timestamp(datetime(2026, 1, 1, 1, tzinfo=UTC)),
                Duration(1, Unit.HOUR),
            ),
            generation_available=energy(0),
            generation_asset_available=True,
            battery_available=True,
            critical_load=energy(1),
            noncritical_load=energy(0),
            grid=GridIntervalLimit(False, True, True, power(2), power(2)),
            dispatch=IntervalDispatch(
                energy(0), energy(0), energy(0), energy(0), energy(0),
                energy(1), energy(0), energy(0),
            ),
        ),
    )
    scenario = SimulationRequest(
        run_id=Identifier("sample-run"),
        schedule_id=Identifier("sample-template"),
        scenario_version_id=Identifier("bundled-sample-v1"),
        alternative_type=AlternativeType.EXISTING,
        intervals=intervals,
        battery=BatterySpec(
            usable_capacity=energy(1),
            minimum_soc=energy(0),
            maximum_soc=energy(1),
            charge_limit=power(1),
            discharge_limit=power(1),
            charge_efficiency=FiniteNumber(1),
            discharge_efficiency=FiniteNumber(1),
            initial_soc=energy(0),
            terminal_treatment=TerminalTreatment(
                TerminalTreatmentKind.MINIMUM, target_soc=energy(0)
            ),
            reserve=energy(0),
            reserve_mode=ReserveMode.OUTAGE_RELEASABLE,
        ),
        minimum_critical_service_fraction=FiniteNumber(0),
    )
    manifest = RunManifest(
        identifier=Identifier("bundled-manifest-v1"),
        scenario_version_id=scenario.scenario_version_id,
        created_at=Timestamp(datetime(2026, 1, 1, tzinfo=UTC)),
        alternative_types=tuple(AlternativeType),
        ordered_interval_ids=tuple(item.interval.identifier for item in intervals),
        input_hashes=(NamedHash("sample", Sha256Digest("a" * 64)),),
        source_record_ids=(Identifier("bundled-source"),),
        pack=VersionReference("massachusetts", "2026.1"),
        policy_snapshot=VersionReference("none", "sample"),
        tariff_configuration=VersionReference(
            BUNDLED_SAMPLE_RATE_CONFIGURATION.identifier.value,
            BUNDLED_SAMPLE_RATE_CONFIGURATION.version,
        ),
        calculation_code=VersionReference("omnigridx", "test"),
        dependencies=(VersionReference("scipy", "1.15.1"),),
        solver=VersionReference("scipy-milp", "1.15.1"),
        solver_settings=(ManifestDecimal("time_limit", FiniteNumber(30), "s"),),
        tolerances=(
            ManifestDecimal(
                "energy_balance", FiniteNumber(Decimal("0.000001")), "kWh"
            ),
        ),
        random_seed=0,
        deployment_mode="demo-local",
        capability_mode=CapabilityStatus.HACKATHON_DEMO,
    )
    return manifest, scenario


def optimization_costs() -> OptimizationCosts:
    rate = BUNDLED_SAMPLE_RATE_CONFIGURATION
    return OptimizationCosts(
        currency="USD",
        interval_rates=tuple(
            IntervalCostRate(rate.import_rate_per_kwh, rate.export_credit_per_kwh)
            for _ in range(2)
        ),
        battery_degradation_per_kwh_throughput=FiniteNumber(Decimal("0.01")),
        critical_unserved_penalty_per_kwh=FiniteNumber(100),
        noncritical_unserved_penalty_per_kwh=FiniteNumber(100),
    )


def factor() -> EmissionsFactor:
    return EmissionsFactor(
        value=FiniteNumber(Decimal("0.4")),
        numerator_unit="kgCO2e",
        denominator_unit="kWh",
        geography="ISO-NE",
        data_year=2022,
        version="sample-v1",
        included_gases=("CO2", "CH4", "N2O"),
        intended_purpose="sample screening",
        source="EPA eGRID sample metadata",
        classification="average",
    )


def clean_attributions(schedule: Schedule) -> tuple[CleanEnergyAttribution, ...]:
    values: list[CleanEnergyAttribution] = []
    for interval in schedule.intervals:
        served = interval.served_critical_load.value + interval.served_noncritical_load.value
        direct = max(
            Decimal(0),
            interval.generation_dispatched.value
            - interval.battery_charge.value
            - interval.grid_export.value,
        )
        values.append(
            CleanEnergyAttribution(
                interval.interval_id,
                energy(min(served, direct)),
                interval.battery_discharge,
            )
        )
    return tuple(values)


def run(
    check: ConstraintChecker,
) -> tuple[RunManifest, ThreeAlternativeComparison]:
    manifest, scenario = sample()
    optimizer = CostMinimizingOptimizer(ScipyMilpSolver(), checker())
    comparison = RunOrchestrator(check, optimizer).run(
        manifest,
        scenario,
        optimization_costs(),
        BUNDLED_SAMPLE_RATE_CONFIGURATION,
        OutageDeclaration(
            Timestamp(datetime(2026, 1, 1, 1, tzinfo=UTC)),
            Duration(1, Unit.HOUR),
        ),
        factor(),
        clean_attributions,
    )
    return manifest, comparison


def test_rejects_scenario_inputs_not_shared_with_the_manifest() -> None:
    manifest, scenario = sample()
    mismatched_scenario = replace(
        scenario, scenario_version_id=Identifier("different-scenario-version")
    )

    with pytest.raises(
        ValueError, match="scenario must match the bundled run manifest"
    ):
        RunOrchestrator(
            checker(), CostMinimizingOptimizer(ScipyMilpSolver(), checker())
        ).run(
            manifest,
            mismatched_scenario,
            optimization_costs(),
            BUNDLED_SAMPLE_RATE_CONFIGURATION,
            None,
            factor(),
            clean_attributions,
        )


def test_publishes_exactly_three_checked_alternatives_with_all_required_metrics() -> None:
    manifest, comparison = run(checker())

    assert comparison.manifest is manifest
    assert tuple(value.alternative for value in comparison.alternatives) == tuple(
        AlternativeType
    )
    assert comparison.recommendation is None
    assert all(value.checker_report.passed for value in comparison.alternatives)
    assert all(
        value.schedule.scenario_version_id == manifest.scenario_version_id
        and tuple(item.interval_id for item in value.schedule.intervals)
        == manifest.ordered_interval_ids
        for value in comparison.alternatives
    )
    assert all(
        value.operating_cost.rate_configuration
        == BUNDLED_SAMPLE_RATE_CONFIGURATION
        for value in comparison.alternatives
    )
    assert comparison.alternatives[0].peak_import == power(1)
    assert comparison.alternatives[0].purchased_electricity_emissions.estimate.value == Decimal("0.4")
    assert comparison.alternatives[0].outage_service.critical_unserved_energy == energy(1)
    assert comparison.alternatives[0].clean_energy_share.share == FiniteNumber(0)
    assert all(value.critical_service_fraction is not None for value in comparison.alternatives)
    assert tuple(value.solver_outcome is not None for value in comparison.alternatives) == (
        False,
        False,
        True,
    )
    assert comparison.alternatives[2].solver_outcome is not None
    assert comparison.alternatives[2].solver_outcome.status is OptimizationStatus.OPTIMAL


class RejectOptimizedChecker(ConstraintChecker):
    def check(self, request: SimulationRequest, candidate: Schedule) -> ConstraintReport:
        report = super().check(request, candidate)
        if candidate.alternative_type is AlternativeType.OPTIMIZED:
            return ConstraintReport(report.tolerance_version, report.diagnostics, None)
        return report


def test_publishes_nothing_when_any_independent_check_fails() -> None:
    tolerance = energy("0.000001")
    rejecting = RejectOptimizedChecker(
        ConstraintTolerances("2026.1", tolerance, tolerance, tolerance, tolerance)
    )

    with pytest.raises(
        OrchestrationError, match="optimized alternative failed independent checking"
    ):
        run(rejecting)
