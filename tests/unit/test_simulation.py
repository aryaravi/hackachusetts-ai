from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from omnigridx.domain import (
    AlternativeType,
    BatterySpec,
    Duration,
    Energy,
    FiniteNumber,
    GridIntervalLimit,
    Identifier,
    Interval,
    IntervalDispatch,
    Power,
    ReserveMode,
    SimulationEngine,
    SimulationError,
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


def battery(
    *,
    terminal: TerminalTreatment | None = None,
    reserve_mode: ReserveMode = ReserveMode.OUTAGE_RELEASABLE,
) -> BatterySpec:
    return BatterySpec(
        usable_capacity=energy(10),
        minimum_soc=energy(1),
        maximum_soc=energy(10),
        charge_limit=power(4),
        discharge_limit=power(6),
        charge_efficiency=FiniteNumber(Decimal("0.8")),
        discharge_efficiency=FiniteNumber(Decimal("0.9")),
        initial_soc=energy(5),
        terminal_treatment=terminal
        or TerminalTreatment(TerminalTreatmentKind.MINIMUM, target_soc=energy(3)),
        reserve=energy(3),
        reserve_mode=reserve_mode,
    )


def interval_input(
    identifier: str,
    *,
    start_hour: int = 0,
    generation_available: str | int = 0,
    generation_dispatched: str | int = 0,
    grid_import: str | int = 0,
    grid_export: str | int = 0,
    battery_charge: str | int = 0,
    battery_discharge: str | int = 0,
    critical_load: str | int = 0,
    noncritical_load: str | int = 0,
    critical_unserved: str | int = 0,
    noncritical_unserved: str | int = 0,
    other_loss: str | int = 0,
    generation_asset_available: bool = True,
    battery_available: bool = True,
    grid_available: bool = True,
    import_allowed: bool = True,
    export_allowed: bool = True,
    import_limit_kw: str | int | None = 4,
    export_limit_kw: str | int | None = 4,
) -> SimulationIntervalInput:
    return SimulationIntervalInput(
        interval=Interval(
            Identifier(identifier),
            Timestamp(datetime(2026, 1, 1, start_hour, tzinfo=UTC)),
            Duration(Decimal("0.5"), Unit.HOUR),
        ),
        generation_available=energy(generation_available),
        generation_asset_available=generation_asset_available,
        battery_available=battery_available,
        critical_load=energy(critical_load),
        noncritical_load=energy(noncritical_load),
        grid=GridIntervalLimit(
            available=grid_available,
            import_allowed=import_allowed,
            export_allowed=export_allowed,
            import_limit=None if import_limit_kw is None else power(import_limit_kw),
            export_limit=None if export_limit_kw is None else power(export_limit_kw),
        ),
        dispatch=IntervalDispatch(
            generation_dispatched=energy(generation_dispatched),
            grid_import=energy(grid_import),
            grid_export=energy(grid_export),
            battery_charge=energy(battery_charge),
            battery_discharge=energy(battery_discharge),
            critical_unserved_load=energy(critical_unserved),
            noncritical_unserved_load=energy(noncritical_unserved),
            other_conversion_loss=energy(other_loss),
        ),
    )


def request(
    intervals: tuple[SimulationIntervalInput, ...],
    *,
    battery_spec: BatterySpec | None = None,
    simultaneous_grid: bool = False,
    simultaneous_battery: bool = False,
    minimum_critical_service: str = "0.5",
) -> SimulationRequest:
    return SimulationRequest(
        run_id=Identifier("run-1"),
        schedule_id=Identifier("schedule-1"),
        scenario_version_id=Identifier("scenario-1"),
        alternative_type=AlternativeType.EXISTING,
        intervals=intervals,
        battery=battery_spec or battery(),
        minimum_critical_service_fraction=FiniteNumber(
            Decimal(minimum_critical_service)
        ),
        simultaneous_grid_flows_allowed=simultaneous_grid,
        simultaneous_battery_flows_allowed=simultaneous_battery,
    )


def test_simulation_produces_one_complete_derived_record_per_interval() -> None:
    inputs = (
        interval_input(
            "i-1",
            generation_available=3,
            generation_dispatched=2,
            grid_import=2,
            critical_load=2,
            noncritical_load=2,
        ),
        interval_input(
            "i-2",
            start_hour=1,
            battery_discharge="1.8",
            critical_load=1,
            noncritical_load="0.8",
            grid_available=False,
        ),
    )

    schedule = SimulationEngine().simulate(request(inputs))

    assert tuple(result.interval_id for result in schedule.intervals) == (
        Identifier("i-1"),
        Identifier("i-2"),
    )
    first, second = schedule.intervals
    assert first.generation_curtailed == energy(1)
    assert first.served_critical_load == energy(2)
    assert first.served_noncritical_load == energy(2)
    assert second.state_of_charge_start == energy(5)
    assert second.state_of_charge_end == energy(3)
    assert abs(
        second.storage_conversion_loss.value - Decimal("0.2")
    ) <= Decimal("1e-12")
    assert all(not result.constraint_check_passed for result in schedule.intervals)


def test_duration_adjusted_grid_and_battery_power_bounds_are_enforced() -> None:
    value = interval_input(
        "i-1",
        grid_import="2.1",
        battery_discharge="3.1",
        critical_load="5.2",
    )

    with pytest.raises(SimulationError) as caught:
        SimulationEngine().simulate(request((value,)))

    constraints = {diagnostic.constraint for diagnostic in caught.value.diagnostics}
    assert {"grid_import_bound", "battery_discharge_bound"} <= constraints


def test_unavailable_assets_permissions_and_direction_rules_report_all_violations() -> None:
    value = interval_input(
        "i-1",
        generation_available=2,
        generation_dispatched=1,
        grid_import=1,
        grid_export=1,
        battery_charge=1,
        battery_discharge=1,
        generation_asset_available=False,
        battery_available=False,
        grid_available=False,
    )

    with pytest.raises(SimulationError) as caught:
        SimulationEngine().simulate(request((value,)))

    constraints = {diagnostic.constraint for diagnostic in caught.value.diagnostics}
    assert {
        "generation_dispatch",
        "grid_import_bound",
        "grid_export_bound",
        "grid_direction",
        "battery_charge_bound",
        "battery_discharge_bound",
        "battery_direction",
    } <= constraints


def test_reserve_is_releasable_only_during_an_outage() -> None:
    terminal_value = TerminalTreatment(
        TerminalTreatmentKind.VALUE,
        value_per_kwh=FiniteNumber(1),
        currency="USD",
    )
    outage = interval_input(
        "i-1",
        battery_discharge="2.7",
        critical_load="2.7",
        grid_available=False,
    )
    value = request((outage,), battery_spec=battery(terminal=terminal_value))
    assert SimulationEngine().simulate(value).intervals[0].state_of_charge_end == energy(2)

    with pytest.raises(SimulationError, match="state_of_charge"):
        SimulationEngine().simulate(
            replace(value, intervals=(replace(outage, grid=replace(outage.grid, available=True)),))
        )


def test_terminal_soc_critical_service_and_conservation_are_hard_constraints() -> None:
    value = interval_input(
        "i-1",
        grid_import=1,
        critical_load=2,
        critical_unserved="1.5",
    )

    with pytest.raises(SimulationError) as caught:
        SimulationEngine().simulate(
            request(
                (value,),
                battery_spec=battery(
                    terminal=TerminalTreatment(
                        TerminalTreatmentKind.EQUALITY,
                        target_soc=energy(3),
                    )
                ),
                minimum_critical_service="0.75",
            )
        )

    constraints = {diagnostic.constraint for diagnostic in caught.value.diagnostics}
    assert {"critical_service", "energy_conservation", "terminal_soc"} <= constraints

    quantity_input = interval_input(
        "quantity",
        grid_import="1.4",
        critical_load=2,
        critical_unserved="0.6",
    )
    with pytest.raises(SimulationError, match="critical_service"):
        SimulationEngine().simulate(
            replace(
                request((quantity_input,)),
                minimum_critical_service_fraction=None,
                minimum_critical_service_quantity=energy("1.5"),
            )
        )


def test_explicit_unbounded_grid_limit_and_allowed_simultaneous_flows_are_supported() -> None:
    value = interval_input(
        "i-1",
        grid_import=101,
        grid_export=1,
        battery_charge=1,
        battery_discharge=1,
        critical_load=100,
        import_limit_kw=None,
    )

    schedule = SimulationEngine().simulate(
        request(
            (value,),
            simultaneous_grid=True,
            simultaneous_battery=True,
        )
    )
    assert schedule.intervals[0].grid_import == energy(101)


def test_missing_inputs_and_duplicate_intervals_reject_without_a_partial_schedule() -> None:
    with pytest.raises(SimulationError) as caught:
        SimulationEngine().simulate(
            replace(request(()), battery=None)
        )
    assert [diagnostic.message for diagnostic in caught.value.diagnostics] == [
        "intervals are required",
        "battery specification is required",
    ]

    duplicate = interval_input("same")
    with pytest.raises(SimulationError, match="unique"):
        SimulationEngine().simulate(request((duplicate, duplicate)))


def test_battery_configuration_rejects_invalid_efficiency_and_terminal_reserve() -> None:
    with pytest.raises(ValueError, match="charge_efficiency"):
        replace(battery(), charge_efficiency=FiniteNumber(0))

    with pytest.raises(ValueError, match="terminal reserve"):
        battery(
            terminal=TerminalTreatment(
                TerminalTreatmentKind.MINIMUM,
                target_soc=energy(2),
            ),
            reserve_mode=ReserveMode.TERMINAL,
        )
