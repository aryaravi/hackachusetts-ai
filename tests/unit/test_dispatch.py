from datetime import UTC, datetime
from decimal import Decimal

from omnigridx.application import (
    EXISTING_OPERATION_VERSION,
    RULE_BASED_DISPATCH_VERSION,
    ExistingDispatch,
    RuleBasedDispatch,
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


def checker() -> ConstraintChecker:
    tolerance = energy("0.000001")
    return ConstraintChecker(
        ConstraintTolerances("2026.1", tolerance, tolerance, tolerance, tolerance)
    )


def interval(
    identifier: str,
    hour: int,
    *,
    generation: str | int,
    critical_load: str | int,
    noncritical_load: str | int,
    baseline: IntervalDispatch,
    grid_available: bool = True,
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
        noncritical_load=energy(noncritical_load),
        grid=GridIntervalLimit(
            available=grid_available,
            import_allowed=True,
            export_allowed=True,
            import_limit=power(4),
            export_limit=power(4),
        ),
        dispatch=baseline,
    )


def baseline(
    generation: str | int,
    *,
    grid_import: str | int = 0,
    grid_export: str | int = 0,
    critical_unserved: str | int = 0,
    noncritical_unserved: str | int = 0,
) -> IntervalDispatch:
    return IntervalDispatch(
        generation_dispatched=energy(generation),
        grid_import=energy(grid_import),
        grid_export=energy(grid_export),
        battery_charge=energy(0),
        battery_discharge=energy(0),
        critical_unserved_load=energy(critical_unserved),
        noncritical_unserved_load=energy(noncritical_unserved),
        other_conversion_loss=energy(0),
    )


def frozen_sample() -> SimulationRequest:
    battery = BatterySpec(
        usable_capacity=energy(8),
        minimum_soc=energy(1),
        maximum_soc=energy(8),
        charge_limit=power(4),
        discharge_limit=power(4),
        charge_efficiency=FiniteNumber(1),
        discharge_efficiency=FiniteNumber(1),
        initial_soc=energy(4),
        terminal_treatment=TerminalTreatment(
            TerminalTreatmentKind.VALUE,
            value_per_kwh=FiniteNumber(0),
            currency="USD",
        ),
        reserve=energy(2),
        reserve_mode=ReserveMode.OUTAGE_RELEASABLE,
    )
    return SimulationRequest(
        run_id=Identifier("sample-run"),
        schedule_id=Identifier("unused-template-schedule"),
        scenario_version_id=Identifier("bundled-ma-sample-v1"),
        alternative_type=AlternativeType.OPTIMIZED,
        intervals=(
            interval(
                "sunny",
                0,
                generation=6,
                critical_load=1,
                noncritical_load=2,
                baseline=baseline(5, grid_export=2),
            ),
            interval(
                "evening",
                1,
                generation=1,
                critical_load=2,
                noncritical_load=3,
                baseline=baseline(1, grid_import=4),
            ),
            interval(
                "outage",
                2,
                generation=1,
                critical_load=2,
                noncritical_load=1,
                baseline=baseline(1, critical_unserved=1, noncritical_unserved=1),
                grid_available=False,
            ),
        ),
        battery=battery,
        minimum_critical_service_fraction=FiniteNumber(Decimal("0.5")),
    )


def test_existing_dispatch_replays_the_frozen_operation_and_passes_checking() -> None:
    schedule = ExistingDispatch(checker()).run(frozen_sample())

    assert isinstance(schedule, Schedule)
    assert schedule.alternative_type is AlternativeType.EXISTING
    assert schedule.identifier == Identifier(
        f"bundled-ma-sample-v1-existing-{EXISTING_OPERATION_VERSION}"
    )
    assert tuple(item.grid_import.value for item in schedule.intervals) == (
        Decimal(0),
        Decimal(4),
        Decimal(0),
    )
    assert tuple(item.grid_export.value for item in schedule.intervals) == (
        Decimal(2),
        Decimal(0),
        Decimal(0),
    )
    assert tuple(item.critical_unserved_load.value for item in schedule.intervals) == (
        Decimal(0),
        Decimal(0),
        Decimal(1),
    )
    assert all(item.constraint_check_passed for item in schedule.intervals)


def test_versioned_rule_uses_solar_then_storage_before_grid_and_passes_checking() -> None:
    strategy = RuleBasedDispatch(checker())

    schedule = strategy.run(frozen_sample())

    assert strategy.version == RULE_BASED_DISPATCH_VERSION
    assert schedule.alternative_type is AlternativeType.RULE_BASED
    assert schedule.identifier == Identifier(
        f"bundled-ma-sample-v1-rule_based-{RULE_BASED_DISPATCH_VERSION}"
    )
    assert tuple(item.battery_charge.value for item in schedule.intervals) == (
        Decimal(3),
        Decimal(0),
        Decimal(0),
    )
    assert tuple(item.battery_discharge.value for item in schedule.intervals) == (
        Decimal(0),
        Decimal(4),
        Decimal(2),
    )
    assert tuple(item.grid_import.value for item in schedule.intervals) == (
        Decimal(0),
        Decimal(0),
        Decimal(0),
    )
    assert tuple(item.state_of_charge_end.value for item in schedule.intervals) == (
        Decimal(7),
        Decimal(3),
        Decimal(1),
    )
    assert all(item.critical_unserved_load.value == 0 for item in schedule.intervals)
    assert all(item.noncritical_unserved_load.value == 0 for item in schedule.intervals)
    assert all(item.constraint_check_passed for item in schedule.intervals)
