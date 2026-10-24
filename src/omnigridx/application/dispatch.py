"""Deterministic dispatch strategies for the bundled judge scenario."""

from dataclasses import dataclass, replace
from decimal import Decimal

from omnigridx.domain.constraints import ConstraintChecker, ConstraintReport
from omnigridx.domain.records import AlternativeType, Schedule
from omnigridx.domain.simulation import (
    IntervalDispatch,
    ReserveMode,
    SimulationEngine,
    SimulationIntervalInput,
    SimulationRequest,
    TerminalTreatmentKind,
)
from omnigridx.domain.values import Energy, Identifier, Unit

EXISTING_OPERATION_VERSION = "existing-operation-v1"
RULE_BASED_DISPATCH_VERSION = "solar-self-consumption-v1"


class DispatchError(RuntimeError):
    """A candidate schedule that failed its independent constraint check."""

    def __init__(self, report: ConstraintReport) -> None:
        self.report = report
        constraints = ", ".join(item.constraint for item in report.diagnostics)
        super().__init__(f"independent constraint check failed: {constraints}")


def _energy(value: Decimal) -> Energy:
    return Energy(value, Unit.KILOWATT_HOUR)


def _schedule_id(
    request: SimulationRequest,
    alternative: AlternativeType,
    version: str,
) -> Identifier:
    return Identifier(f"{request.scenario_version_id.value}-{alternative.value}-{version}")


def _checked_schedule(
    request: SimulationRequest,
    checker: ConstraintChecker,
) -> Schedule:
    candidate = SimulationEngine().simulate(request)
    report = checker.check(request, candidate)
    if report.checked_schedule is None:
        raise DispatchError(report)
    return report.checked_schedule


@dataclass(frozen=True, slots=True)
class ExistingDispatch:
    """Replay the documented operation frozen in each scenario interval."""

    checker: ConstraintChecker
    version: str = EXISTING_OPERATION_VERSION

    def run(self, scenario: SimulationRequest) -> Schedule:
        request = replace(
            scenario,
            schedule_id=_schedule_id(scenario, AlternativeType.EXISTING, self.version),
            alternative_type=AlternativeType.EXISTING,
        )
        return _checked_schedule(request, self.checker)


@dataclass(frozen=True, slots=True)
class RuleBasedDispatch:
    """Solar serves load, then charges; battery serves deficits before the grid."""

    checker: ConstraintChecker
    version: str = RULE_BASED_DISPATCH_VERSION

    def run(self, scenario: SimulationRequest) -> Schedule:
        state_of_charge = scenario.battery.initial_soc.value if scenario.battery else Decimal(0)
        intervals: list[SimulationIntervalInput] = []
        for item in scenario.intervals:
            dispatch, state_of_charge = self._dispatch(item, scenario, state_of_charge)
            intervals.append(replace(item, dispatch=dispatch))

        request = replace(
            scenario,
            schedule_id=_schedule_id(scenario, AlternativeType.RULE_BASED, self.version),
            alternative_type=AlternativeType.RULE_BASED,
            intervals=tuple(intervals),
        )
        return _checked_schedule(request, self.checker)

    @staticmethod
    def _dispatch(
        item: SimulationIntervalInput,
        scenario: SimulationRequest,
        state_of_charge: Decimal,
    ) -> tuple[IntervalDispatch, Decimal]:
        battery = scenario.battery
        if battery is None:
            return item.dispatch, state_of_charge

        duration = item.interval.duration.value
        generation = (
            item.generation_available.value if item.generation_asset_available else Decimal(0)
        )
        critical_load = item.critical_load.value
        noncritical_load = item.noncritical_load.value
        total_load = critical_load + noncritical_load
        direct_generation = min(generation, total_load)
        surplus = generation - direct_generation
        deficit = total_load - direct_generation

        reserve_floor = battery.minimum_soc.value
        if battery.reserve_mode is ReserveMode.UNAVAILABLE_FOR_NORMAL_DISPATCH or (
            battery.reserve_mode is ReserveMode.OUTAGE_RELEASABLE and item.grid.available
        ):
            reserve_floor = max(reserve_floor, battery.reserve.value)
        terminal = battery.terminal_treatment
        if terminal.kind in (TerminalTreatmentKind.MINIMUM, TerminalTreatmentKind.EQUALITY):
            assert terminal.target_soc is not None
            reserve_floor = max(reserve_floor, terminal.target_soc.value)

        charge_ceiling = battery.maximum_soc.value
        if terminal.kind is TerminalTreatmentKind.EQUALITY:
            assert terminal.target_soc is not None
            charge_ceiling = terminal.target_soc.value

        battery_charge = Decimal(0)
        battery_discharge = Decimal(0)
        if item.battery_available:
            battery_charge = min(
                surplus,
                battery.charge_limit.value * duration,
                max(
                    Decimal(0),
                    (charge_ceiling - state_of_charge) / battery.charge_efficiency.value,
                ),
            )
            state_of_charge += battery.charge_efficiency.value * battery_charge
            surplus -= battery_charge

            battery_discharge = min(
                deficit,
                battery.discharge_limit.value * duration,
                max(
                    Decimal(0),
                    (state_of_charge - reserve_floor) * battery.discharge_efficiency.value,
                ),
            )
            state_of_charge -= battery_discharge / battery.discharge_efficiency.value
            deficit -= battery_discharge

        import_bound = RuleBasedDispatch._grid_bound(
            item.grid.available,
            item.grid.import_allowed,
            item.grid.import_limit.value if item.grid.import_limit else None,
            duration,
            deficit,
        )
        grid_import = min(deficit, import_bound)
        supplied_load = total_load - (deficit - grid_import)
        served_critical = min(critical_load, supplied_load)
        served_noncritical = min(noncritical_load, supplied_load - served_critical)

        export_bound = RuleBasedDispatch._grid_bound(
            item.grid.available,
            item.grid.export_allowed,
            item.grid.export_limit.value if item.grid.export_limit else None,
            duration,
            surplus,
        )
        grid_export = min(surplus, export_bound)
        generation_dispatched = direct_generation + battery_charge + grid_export

        return (
            IntervalDispatch(
                generation_dispatched=_energy(generation_dispatched),
                grid_import=_energy(grid_import),
                grid_export=_energy(grid_export),
                battery_charge=_energy(battery_charge),
                battery_discharge=_energy(battery_discharge),
                critical_unserved_load=_energy(critical_load - served_critical),
                noncritical_unserved_load=_energy(noncritical_load - served_noncritical),
                other_conversion_loss=_energy(Decimal(0)),
            ),
            state_of_charge,
        )

    @staticmethod
    def _grid_bound(
        available: bool,
        allowed: bool,
        limit_kw: Decimal | None,
        duration: Decimal,
        required: Decimal,
    ) -> Decimal:
        if not available or not allowed:
            return Decimal(0)
        return required if limit_kw is None else limit_kw * duration
