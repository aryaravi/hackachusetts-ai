from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from omnigridx.domain import (
    AlternativeType,
    BatterySpec,
    ConstraintChecker,
    ConstraintTolerances,
    Duration,
    Energy,
    FiniteNumber,
    GridIntervalLimit,
    Identifier,
    Interval,
    IntervalDispatch,
    Power,
    ReserveMode,
    Schedule,
    SimulationEngine,
    SimulationIntervalInput,
    SimulationRequest,
    TerminalTreatment,
    TerminalTreatmentKind,
    Timestamp,
    Unit,
)


def energy(value: str | int) -> Energy:
    return Energy(Decimal(value), Unit.KILOWATT_HOUR)


def power(value: str | int) -> Power:
    return Power(Decimal(value), Unit.KILOWATT)


def tolerances(value: str = "0.000001") -> ConstraintTolerances:
    tolerance = energy(value)
    return ConstraintTolerances("2026.1", tolerance, tolerance, tolerance, tolerance)


def interval_input(
    identifier: str,
    start_hour: int,
    *,
    generation_available: str | int,
    generation_dispatched: str | int,
    grid_import: str | int = 0,
    battery_charge: str | int = 0,
    battery_discharge: str | int = 0,
    critical_load: str | int,
    noncritical_load: str | int = 0,
    critical_unserved: str | int = 0,
    grid_available: bool = True,
) -> SimulationIntervalInput:
    return SimulationIntervalInput(
        interval=Interval(
            Identifier(identifier),
            Timestamp(datetime(2026, 1, 1, start_hour, tzinfo=UTC)),
            Duration(1, Unit.HOUR),
        ),
        generation_available=energy(generation_available),
        generation_asset_available=True,
        battery_available=True,
        critical_load=energy(critical_load),
        noncritical_load=energy(noncritical_load),
        grid=GridIntervalLimit(
            available=grid_available,
            import_allowed=True,
            export_allowed=True,
            import_limit=power(2),
            export_limit=power(2),
        ),
        dispatch=IntervalDispatch(
            generation_dispatched=energy(generation_dispatched),
            grid_import=energy(grid_import),
            grid_export=energy(0),
            battery_charge=energy(battery_charge),
            battery_discharge=energy(battery_discharge),
            critical_unserved_load=energy(critical_unserved),
            noncritical_unserved_load=energy(0),
            other_conversion_loss=energy(0),
        ),
    )


def request() -> SimulationRequest:
    battery = BatterySpec(
        usable_capacity=energy(10),
        minimum_soc=energy(1),
        maximum_soc=energy(10),
        charge_limit=power(2),
        discharge_limit=power(2),
        charge_efficiency=FiniteNumber(Decimal("0.8")),
        discharge_efficiency=FiniteNumber(Decimal("0.9")),
        initial_soc=energy(5),
        terminal_treatment=TerminalTreatment(
            TerminalTreatmentKind.MINIMUM,
            target_soc=energy(3),
        ),
        reserve=energy(3),
        reserve_mode=ReserveMode.UNAVAILABLE_FOR_NORMAL_DISPATCH,
    )
    return SimulationRequest(
        run_id=Identifier("run-1"),
        schedule_id=Identifier("schedule-1"),
        scenario_version_id=Identifier("scenario-1"),
        alternative_type=AlternativeType.EXISTING,
        intervals=(
            interval_input(
                "i-1",
                0,
                generation_available=2,
                generation_dispatched=2,
                grid_import=1,
                battery_charge=1,
                critical_load=2,
            ),
            interval_input(
                "i-2",
                1,
                generation_available=0,
                generation_dispatched=0,
                battery_discharge="1.8",
                critical_load=2,
                noncritical_load="0.3",
                critical_unserved="0.5",
                grid_available=False,
            ),
        ),
        battery=battery,
        minimum_critical_service_fraction=FiniteNumber(Decimal("0.75")),
    )


def changed_result(schedule: Schedule, index: int, **changes: Any) -> Schedule:
    intervals = list(schedule.intervals)
    intervals[index] = replace(intervals[index], **changes)
    return replace(schedule, intervals=tuple(intervals))


def assert_numeric_violation(
    value: SimulationRequest,
    candidate: Schedule,
    constraint: str,
) -> None:
    report = ConstraintChecker(tolerances()).check(value, candidate)
    matching = [item for item in report.diagnostics if item.constraint == constraint]

    assert not report.passed
    assert report.checked_schedule is None
    assert matching
    assert all(item.interval_id is not None for item in matching)
    assert all(item.residual is not None and item.tolerance is not None for item in matching)


def test_checker_accepts_a_valid_multi_interval_schedule_and_marks_every_interval() -> None:
    value = request()
    candidate = SimulationEngine().simulate(value)

    report = ConstraintChecker(tolerances()).check(value, candidate)

    assert report.passed
    assert report.tolerance_version == "2026.1"
    assert report.diagnostics == ()
    assert report.checked_schedule is not None
    assert len(report.checked_schedule.intervals) == 2
    assert all(item.constraint_check_passed for item in report.checked_schedule.intervals)
    assert all(not item.constraint_check_passed for item in candidate.intervals)


@pytest.mark.parametrize(
    ("index", "changes", "constraint"),
    (
        (0, {"generation_available": energy(3), "generation_curtailed": energy(1)}, "generation_available"),
        (0, {"generation_curtailed": energy("0.1")}, "generation_decomposition"),
        (
            0,
            {"served_critical_load": energy("1.9"), "other_conversion_loss": energy("0.1")},
            "critical_load_decomposition",
        ),
        (
            1,
            {"served_noncritical_load": energy("0.2"), "other_conversion_loss": energy("0.1")},
            "noncritical_load_decomposition",
        ),
    ),
)
def test_checker_rejects_each_reported_input_and_decomposition_violation(
    index: int,
    changes: dict[str, Any],
    constraint: str,
) -> None:
    value = request()
    candidate = changed_result(SimulationEngine().simulate(value), index, **changes)

    assert_numeric_violation(value, candidate, constraint)


def test_checker_rejects_conservation_violation() -> None:
    value = request()
    candidate = changed_result(
        SimulationEngine().simulate(value),
        0,
        other_conversion_loss=energy("0.1"),
    )

    assert_numeric_violation(value, candidate, "energy_conservation")


def test_checker_rejects_grid_asset_storage_reserve_and_service_bounds() -> None:
    value = request()
    candidate = SimulationEngine().simulate(value)
    first, second = value.intervals
    battery = value.battery
    assert battery is not None
    cases = (
        (
            "generation_dispatch",
            replace(value, intervals=(replace(first, generation_asset_available=False), second)),
        ),
        (
            "grid_import_bound",
            replace(
                value,
                intervals=(
                    replace(first, grid=replace(first.grid, import_limit=power("0.5"))),
                    second,
                ),
            ),
        ),
        (
            "battery_charge_bound",
            replace(value, battery=replace(battery, charge_limit=power("0.5"))),
        ),
        (
            "state_of_charge_end_bound",
            replace(value, battery=replace(battery, reserve=energy(5))),
        ),
        (
            "state_of_charge_end_bound",
            replace(value, battery=replace(battery, maximum_soc=energy("5.5"))),
        ),
        (
            "critical_service",
            replace(value, minimum_critical_service_fraction=FiniteNumber(1)),
        ),
    )

    for constraint, changed_request in cases:
        assert_numeric_violation(changed_request, candidate, constraint)


def test_checker_rejects_soc_transition_and_storage_loss_violations() -> None:
    value = request()
    candidate = SimulationEngine().simulate(value)
    first = changed_result(candidate, 0, state_of_charge_end=energy("5.7"))
    transition_broken = changed_result(
        first,
        1,
        state_of_charge_start=energy("5.7"),
        state_of_charge_end=energy("3.7"),
    )

    assert_numeric_violation(value, transition_broken, "state_of_charge_transition")
    assert_numeric_violation(
        value,
        changed_result(candidate, 0, storage_conversion_loss=energy("0.21")),
        "storage_conversion_loss",
    )


@pytest.mark.parametrize(
    ("index", "changes", "constraint"),
    (
        (
            0,
            {"grid_import": energy("1.5"), "grid_export": energy("0.5")},
            "grid_direction",
        ),
        (
            0,
            {
                "grid_import": energy("1.28"),
                "battery_charge": energy(2),
                "battery_discharge": energy("0.72"),
                "storage_conversion_loss": energy("0.48"),
            },
            "battery_direction",
        ),
    ),
)
def test_checker_rejects_unsupported_simultaneous_flow_directions(
    index: int,
    changes: dict[str, Any],
    constraint: str,
) -> None:
    value = request()
    candidate = changed_result(SimulationEngine().simulate(value), index, **changes)

    assert_numeric_violation(value, candidate, constraint)


def test_checker_rejects_terminal_treatment_violation() -> None:
    value = request()
    battery = value.battery
    assert battery is not None
    changed_request = replace(
        value,
        battery=replace(
            battery,
            terminal_treatment=TerminalTreatment(
                TerminalTreatmentKind.EQUALITY,
                target_soc=energy(4),
            ),
        ),
    )

    assert_numeric_violation(
        changed_request,
        SimulationEngine().simulate(value),
        "terminal_soc",
    )


def test_checker_rejects_incomplete_candidate_without_partial_checked_schedule() -> None:
    value = request()
    candidate = SimulationEngine().simulate(value)

    report = ConstraintChecker(tolerances()).check(
        value,
        replace(candidate, intervals=(candidate.intervals[0],)),
    )

    assert not report.passed
    assert report.checked_schedule is None
    assert report.diagnostics == (
        report.diagnostics[0],
    )
    diagnostic = report.diagnostics[0]
    assert diagnostic.interval_id == Identifier("i-2")
    assert diagnostic.constraint == "interval_cardinality"
    assert diagnostic.residual is None
    assert diagnostic.tolerance is None


def test_checker_accepts_residual_at_tolerance_and_rejects_residual_above_it() -> None:
    value = request()
    candidate = SimulationEngine().simulate(value)
    checker = ConstraintChecker(tolerances("0.1"))

    at_tolerance = changed_result(candidate, 0, other_conversion_loss=energy("0.1"))
    assert checker.check(value, at_tolerance).passed

    above_tolerance = changed_result(
        candidate,
        0,
        other_conversion_loss=energy("0.1001"),
    )
    report = checker.check(value, above_tolerance)

    assert not report.passed
    assert [diagnostic.constraint for diagnostic in report.diagnostics] == [
        "energy_conservation"
    ]
    assert report.diagnostics[0].interval_id == Identifier("i-1")
    assert report.diagnostics[0].residual == energy("0.1001")
    assert report.diagnostics[0].tolerance == energy("0.1")
