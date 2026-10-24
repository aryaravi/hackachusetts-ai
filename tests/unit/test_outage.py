from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from omnigridx.application import (
    OUTAGE_SERVICE_DISCLOSURE,
    OUTAGE_SERVICE_LABEL,
    OutageDeclaration,
    OutageMetricsCalculator,
    OutageServiceError,
    OutageServiceStatus,
)
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


def interval(
    identifier: str,
    hour: int,
    *,
    generation: str | int,
    critical_load: str | int,
    critical_unserved: str | int,
    grid_available: bool,
    grid_import: str | int = 0,
    import_limit: Power | None = None,
) -> SimulationIntervalInput:
    return SimulationIntervalInput(
        interval=Interval(
            Identifier(identifier),
            Timestamp(datetime(2026, 1, 1, hour, tzinfo=UTC)),
            Duration(1, Unit.HOUR),
        ),
        generation_available=energy(generation),
        generation_asset_available=True,
        battery_available=True,
        critical_load=energy(critical_load),
        noncritical_load=energy(0),
        grid=GridIntervalLimit(
            available=grid_available,
            import_allowed=True,
            export_allowed=True,
            import_limit=import_limit,
            export_limit=power(4),
        ),
        dispatch=IntervalDispatch(
            generation_dispatched=energy(generation),
            grid_import=energy(grid_import),
            grid_export=energy(0),
            battery_charge=energy(0),
            battery_discharge=energy(0),
            critical_unserved_load=energy(critical_unserved),
            noncritical_unserved_load=energy(0),
            other_conversion_loss=energy(0),
        ),
    )


def scenario() -> SimulationRequest:
    return SimulationRequest(
        run_id=Identifier("run-1"),
        schedule_id=Identifier("schedule-1"),
        scenario_version_id=Identifier("sample-scenario-v1"),
        alternative_type=AlternativeType.EXISTING,
        intervals=(
            interval(
                "normal",
                0,
                generation=0,
                critical_load=1,
                critical_unserved=0,
                grid_available=True,
                grid_import=1,
                import_limit=power(4),
            ),
            interval(
                "outage-1",
                1,
                generation=1,
                critical_load=2,
                critical_unserved=1,
                grid_available=False,
                import_limit=power(4),
            ),
            interval(
                "outage-2",
                2,
                generation=2,
                critical_load=2,
                critical_unserved=0,
                grid_available=False,
                import_limit=power(4),
            ),
        ),
        battery=BatterySpec(
            usable_capacity=energy(4),
            minimum_soc=energy(0),
            maximum_soc=energy(4),
            charge_limit=power(2),
            discharge_limit=power(2),
            charge_efficiency=FiniteNumber(1),
            discharge_efficiency=FiniteNumber(1),
            initial_soc=energy(2),
            terminal_treatment=TerminalTreatment(
                TerminalTreatmentKind.VALUE,
                value_per_kwh=FiniteNumber(0),
                currency="USD",
            ),
            reserve=energy(0),
            reserve_mode=ReserveMode.OUTAGE_RELEASABLE,
        ),
        minimum_critical_service_fraction=FiniteNumber(0),
    )


def checked_schedule(value: SimulationRequest) -> Schedule:
    tolerance = energy("0.000001")
    checker = ConstraintChecker(
        ConstraintTolerances("2026.1", tolerance, tolerance, tolerance, tolerance)
    )
    report = checker.check(value, SimulationEngine().simulate(value))
    assert report.checked_schedule is not None
    return report.checked_schedule


def declaration() -> OutageDeclaration:
    return OutageDeclaration(
        start=Timestamp(datetime(2026, 1, 1, 1, tzinfo=UTC)),
        duration=Duration(2, Unit.HOUR),
    )


def test_declared_outage_reports_deterministic_service_and_enforces_zero_grid_bounds() -> None:
    value = scenario()
    schedule = checked_schedule(value)

    result = OutageMetricsCalculator().calculate(value, schedule, declaration())

    assert result.status is OutageServiceStatus.EVALUATED
    assert result.critical_unserved_energy == energy(1)
    assert result.interruption_duration == Duration(1, Unit.HOUR)
    assert result.label == OUTAGE_SERVICE_LABEL
    assert result.disclosure == OUTAGE_SERVICE_DISCLOSURE
    assert "not probabilistic reliability" in result.disclosure
    assert all(
        item.grid_import.value == 0 and item.grid_export.value == 0
        for item in schedule.intervals[1:]
    )

    invalid_interval = replace(schedule.intervals[1], grid_import=energy(1))
    invalid_schedule = replace(
        schedule,
        intervals=(schedule.intervals[0], invalid_interval, schedule.intervals[2]),
    )
    with pytest.raises(OutageServiceError) as error:
        OutageMetricsCalculator().calculate(value, invalid_schedule, declaration())
    assert error.value.issues == (
        "grid_bounds_must_be_zero_while_unavailable:outage-1",
    )


def test_missing_outage_inputs_are_reported_together() -> None:
    value = scenario()
    schedule = checked_schedule(value)
    incomplete = replace(value, intervals=(), battery=None)

    with pytest.raises(OutageServiceError) as error:
        OutageMetricsCalculator().calculate(
            incomplete,
            schedule,
            OutageDeclaration(start=None, duration=None),
        )

    assert error.value.issues == (
        "outage_start",
        "outage_duration",
        "interval_grid_availability",
        "critical_load_profile",
        "equipment_availability",
        "interval_import_bounds",
        "starting_state_of_charge",
        "reserve_behavior",
    )


def test_no_declared_outage_with_unbounded_grid_is_not_evaluated() -> None:
    value = scenario()
    always_available = replace(
        value,
        intervals=tuple(
            replace(item, grid=replace(item.grid, available=True, import_limit=None))
            for item in value.intervals
        ),
    )
    schedule = checked_schedule(always_available)

    result = OutageMetricsCalculator().calculate(always_available, schedule, None)

    assert result.status is OutageServiceStatus.NOT_EVALUATED
    assert result.critical_unserved_energy is None
    assert result.interruption_duration is None
    assert result.label == OUTAGE_SERVICE_LABEL
