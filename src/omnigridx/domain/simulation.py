"""Pure interval energy accounting and hard-constraint validation."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .records import AlternativeType, IntervalResult, Schedule
from .values import Energy, FiniteNumber, Identifier, Interval, Power, Unit


class ReserveMode(StrEnum):
    UNAVAILABLE_FOR_NORMAL_DISPATCH = "unavailable"
    OUTAGE_RELEASABLE = "outage_releasable"
    TERMINAL = "terminal"


class TerminalTreatmentKind(StrEnum):
    MINIMUM = "minimum"
    EQUALITY = "equality"
    VALUE = "value"


@dataclass(frozen=True, slots=True)
class TerminalTreatment:
    kind: TerminalTreatmentKind
    target_soc: Energy | None = None
    value_per_kwh: FiniteNumber | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        if self.kind in (TerminalTreatmentKind.MINIMUM, TerminalTreatmentKind.EQUALITY):
            if self.target_soc is None:
                raise ValueError("terminal minimum/equality treatment requires target_soc")
            if self.value_per_kwh is not None or self.currency is not None:
                raise ValueError("terminal minimum/equality treatment cannot have a value")
        elif self.kind is TerminalTreatmentKind.VALUE:
            if self.target_soc is not None:
                raise ValueError("terminal value treatment cannot have target_soc")
            if self.value_per_kwh is None or not self.currency:
                raise ValueError("terminal value treatment requires value_per_kwh and currency")
        else:
            raise ValueError("unsupported terminal treatment")


@dataclass(frozen=True, slots=True)
class BatterySpec:
    usable_capacity: Energy
    minimum_soc: Energy
    maximum_soc: Energy
    charge_limit: Power
    discharge_limit: Power
    charge_efficiency: FiniteNumber
    discharge_efficiency: FiniteNumber
    initial_soc: Energy
    terminal_treatment: TerminalTreatment
    reserve: Energy
    reserve_mode: ReserveMode

    def __post_init__(self) -> None:
        minimum = self.minimum_soc.value
        maximum = self.maximum_soc.value
        if not Decimal(0) <= minimum <= maximum <= self.usable_capacity.value:
            raise ValueError("battery SOC bounds must satisfy 0 <= minimum <= maximum <= capacity")
        if not minimum <= self.initial_soc.value <= maximum:
            raise ValueError("initial SOC must be within battery bounds")
        if not minimum <= self.reserve.value <= maximum:
            raise ValueError("reserve must be within battery bounds")
        for name, efficiency in (
            ("charge_efficiency", self.charge_efficiency),
            ("discharge_efficiency", self.discharge_efficiency),
        ):
            if not Decimal(0) < efficiency.value <= Decimal(1):
                raise ValueError(f"{name} must be greater than zero and at most one")
        target = self.terminal_treatment.target_soc
        if target is not None and not minimum <= target.value <= maximum:
            raise ValueError("terminal target SOC must be within battery bounds")
        if self.reserve_mode is ReserveMode.TERMINAL and (
            target is None or target.value < self.reserve.value
        ):
            raise ValueError("terminal reserve mode requires a target at least equal to reserve")


@dataclass(frozen=True, slots=True)
class GridIntervalLimit:
    available: bool
    import_allowed: bool
    export_allowed: bool
    import_limit: Power | None
    export_limit: Power | None


@dataclass(frozen=True, slots=True)
class IntervalDispatch:
    generation_dispatched: Energy
    grid_import: Energy
    grid_export: Energy
    battery_charge: Energy
    battery_discharge: Energy
    critical_unserved_load: Energy
    noncritical_unserved_load: Energy
    other_conversion_loss: Energy


@dataclass(frozen=True, slots=True)
class SimulationIntervalInput:
    interval: Interval
    generation_available: Energy
    generation_asset_available: bool
    battery_available: bool
    critical_load: Energy
    noncritical_load: Energy
    grid: GridIntervalLimit
    dispatch: IntervalDispatch


@dataclass(frozen=True, slots=True)
class SimulationRequest:
    run_id: Identifier
    schedule_id: Identifier
    scenario_version_id: Identifier
    alternative_type: AlternativeType
    intervals: tuple[SimulationIntervalInput, ...]
    battery: BatterySpec | None
    minimum_critical_service_fraction: FiniteNumber | None
    minimum_critical_service_quantity: Energy | None = None
    simultaneous_grid_flows_allowed: bool = False
    simultaneous_battery_flows_allowed: bool = False

    def __post_init__(self) -> None:
        fraction = self.minimum_critical_service_fraction
        if (fraction is None) == (self.minimum_critical_service_quantity is None):
            raise ValueError("configure exactly one critical service quantity or fraction")
        if fraction is not None and not Decimal(0) <= fraction.value <= Decimal(1):
            raise ValueError("minimum critical service fraction must be between zero and one")


@dataclass(frozen=True, slots=True)
class SimulationDiagnostic:
    interval_id: Identifier | None
    constraint: str
    message: str


class SimulationError(ValueError):
    """A rejected simulation containing every independently detectable violation."""

    def __init__(self, diagnostics: tuple[SimulationDiagnostic, ...]) -> None:
        self.diagnostics = diagnostics
        detail = "; ".join(
            f"{diagnostic.interval_id or 'scenario'}:{diagnostic.constraint}: {diagnostic.message}"
            for diagnostic in diagnostics
        )
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class _ComputedInterval:
    source: SimulationIntervalInput
    served_critical: Decimal
    served_noncritical: Decimal
    state_of_charge_start: Decimal
    state_of_charge_end: Decimal
    storage_loss: Decimal


class SimulationEngine:
    """Build a complete schedule only when every interval satisfies hard constraints."""

    def simulate(self, request: SimulationRequest) -> Schedule:
        diagnostics: list[SimulationDiagnostic] = []
        if not request.intervals:
            diagnostics.append(
                SimulationDiagnostic(None, "missing_input", "intervals are required")
            )
        if request.battery is None:
            diagnostics.append(
                SimulationDiagnostic(None, "missing_input", "battery specification is required")
            )
        if diagnostics:
            raise SimulationError(tuple(diagnostics))

        battery = request.battery
        assert battery is not None
        interval_ids = tuple(item.interval.identifier for item in request.intervals)
        if len(set(interval_ids)) != len(interval_ids):
            diagnostics.append(
                SimulationDiagnostic(None, "intervals", "interval identifiers must be unique")
            )

        state_of_charge = battery.initial_soc.value
        computed: list[_ComputedInterval] = []
        for item in request.intervals:
            start_soc = state_of_charge
            dispatch = item.dispatch
            duration = item.interval.duration.value
            interval_id = item.interval.identifier
            available_generation = (
                item.generation_available.value if item.generation_asset_available else Decimal(0)
            )
            served_critical = item.critical_load.value - dispatch.critical_unserved_load.value
            served_noncritical = (
                item.noncritical_load.value - dispatch.noncritical_unserved_load.value
            )

            self._at_most(
                diagnostics,
                interval_id,
                "generation_dispatch",
                dispatch.generation_dispatched.value,
                available_generation,
            )
            self._at_most(
                diagnostics,
                interval_id,
                "critical_load_decomposition",
                dispatch.critical_unserved_load.value,
                item.critical_load.value,
            )
            self._at_most(
                diagnostics,
                interval_id,
                "noncritical_load_decomposition",
                dispatch.noncritical_unserved_load.value,
                item.noncritical_load.value,
            )

            import_bound = self._grid_bound(
                item.grid.available,
                item.grid.import_allowed,
                item.grid.import_limit,
                duration,
            )
            export_bound = self._grid_bound(
                item.grid.available,
                item.grid.export_allowed,
                item.grid.export_limit,
                duration,
            )
            self._at_most(
                diagnostics,
                interval_id,
                "grid_import_bound",
                dispatch.grid_import.value,
                import_bound,
            )
            self._at_most(
                diagnostics,
                interval_id,
                "grid_export_bound",
                dispatch.grid_export.value,
                export_bound,
            )
            if (
                not request.simultaneous_grid_flows_allowed
                and dispatch.grid_import.value > 0
                and dispatch.grid_export.value > 0
            ):
                diagnostics.append(
                    SimulationDiagnostic(
                        interval_id,
                        "grid_direction",
                        "simultaneous import and export are not allowed",
                    )
                )

            charge_bound = battery.charge_limit.value * duration
            discharge_bound = battery.discharge_limit.value * duration
            if not item.battery_available:
                charge_bound = discharge_bound = Decimal(0)
            self._at_most(
                diagnostics,
                interval_id,
                "battery_charge_bound",
                dispatch.battery_charge.value,
                charge_bound,
            )
            self._at_most(
                diagnostics,
                interval_id,
                "battery_discharge_bound",
                dispatch.battery_discharge.value,
                discharge_bound,
            )
            if (
                not request.simultaneous_battery_flows_allowed
                and dispatch.battery_charge.value > 0
                and dispatch.battery_discharge.value > 0
            ):
                diagnostics.append(
                    SimulationDiagnostic(
                        interval_id,
                        "battery_direction",
                        "simultaneous charge and discharge are not allowed",
                    )
                )

            storage_loss = (
                (Decimal(1) - battery.charge_efficiency.value)
                * dispatch.battery_charge.value
                + (Decimal(1) / battery.discharge_efficiency.value - Decimal(1))
                * dispatch.battery_discharge.value
            )
            state_of_charge = (
                start_soc
                + battery.charge_efficiency.value * dispatch.battery_charge.value
                - dispatch.battery_discharge.value / battery.discharge_efficiency.value
            )
            reserve_floor = self._reserve_floor(battery, item.grid.available)
            if not reserve_floor <= state_of_charge <= battery.maximum_soc.value:
                diagnostics.append(
                    SimulationDiagnostic(
                        interval_id,
                        "state_of_charge",
                        f"end SOC must be between {reserve_floor} and {battery.maximum_soc.value} kWh",
                    )
                )

            fraction = request.minimum_critical_service_fraction
            if fraction is not None:
                required_critical = item.critical_load.value * fraction.value
            else:
                quantity = request.minimum_critical_service_quantity
                assert quantity is not None
                required_critical = quantity.value
            if served_critical < required_critical:
                diagnostics.append(
                    SimulationDiagnostic(
                        interval_id,
                        "critical_service",
                        f"served critical load must be at least {required_critical} kWh",
                    )
                )

            supply = (
                dispatch.generation_dispatched.value
                + dispatch.grid_import.value
                + dispatch.battery_discharge.value
            )
            use = (
                served_critical
                + served_noncritical
                + dispatch.battery_charge.value
                + dispatch.grid_export.value
                + dispatch.other_conversion_loss.value
            )
            if supply != use:
                diagnostics.append(
                    SimulationDiagnostic(
                        interval_id,
                        "energy_conservation",
                        f"supply {supply} kWh does not equal use {use} kWh",
                    )
                )

            computed.append(
                _ComputedInterval(
                    source=item,
                    served_critical=served_critical,
                    served_noncritical=served_noncritical,
                    state_of_charge_start=start_soc,
                    state_of_charge_end=state_of_charge,
                    storage_loss=storage_loss,
                )
            )

        self._check_terminal_treatment(diagnostics, battery, state_of_charge)
        if diagnostics:
            raise SimulationError(tuple(diagnostics))

        results = tuple(self._result(request, value) for value in computed)
        return Schedule(
            identifier=request.schedule_id,
            scenario_version_id=request.scenario_version_id,
            alternative_type=request.alternative_type,
            intervals=results,
        )

    @staticmethod
    def _at_most(
        diagnostics: list[SimulationDiagnostic],
        interval_id: Identifier,
        constraint: str,
        actual: Decimal,
        maximum: Decimal | None,
    ) -> None:
        if maximum is not None and actual > maximum:
            diagnostics.append(
                SimulationDiagnostic(
                    interval_id,
                    constraint,
                    f"{actual} kWh exceeds {maximum} kWh",
                )
            )

    @staticmethod
    def _grid_bound(
        available: bool,
        allowed: bool,
        limit: Power | None,
        duration: Decimal,
    ) -> Decimal | None:
        if not available or not allowed:
            return Decimal(0)
        return None if limit is None else limit.value * duration

    @staticmethod
    def _reserve_floor(battery: BatterySpec, grid_available: bool) -> Decimal:
        if battery.reserve_mode is ReserveMode.UNAVAILABLE_FOR_NORMAL_DISPATCH:
            return max(battery.minimum_soc.value, battery.reserve.value)
        if battery.reserve_mode is ReserveMode.OUTAGE_RELEASABLE and grid_available:
            return max(battery.minimum_soc.value, battery.reserve.value)
        return battery.minimum_soc.value

    @staticmethod
    def _check_terminal_treatment(
        diagnostics: list[SimulationDiagnostic],
        battery: BatterySpec,
        final_soc: Decimal,
    ) -> None:
        treatment = battery.terminal_treatment
        target = treatment.target_soc
        if treatment.kind is TerminalTreatmentKind.MINIMUM:
            assert target is not None
            if final_soc < target.value:
                diagnostics.append(
                    SimulationDiagnostic(
                        None,
                        "terminal_soc",
                        f"final SOC must be at least {target.value} kWh",
                    )
                )
        elif treatment.kind is TerminalTreatmentKind.EQUALITY:
            assert target is not None
            if final_soc != target.value:
                diagnostics.append(
                    SimulationDiagnostic(
                        None,
                        "terminal_soc",
                        f"final SOC must equal {target.value} kWh",
                    )
                )

    @staticmethod
    def _result(request: SimulationRequest, value: _ComputedInterval) -> IntervalResult:
        source = value.source
        dispatch = source.dispatch
        available = source.generation_available.value
        return IntervalResult(
            run_id=request.run_id,
            alternative_type=request.alternative_type,
            interval_id=source.interval.identifier,
            generation_available=source.generation_available,
            generation_dispatched=dispatch.generation_dispatched,
            generation_curtailed=Energy(
                available - dispatch.generation_dispatched.value,
                Unit.KILOWATT_HOUR,
            ),
            grid_import=dispatch.grid_import,
            grid_export=dispatch.grid_export,
            battery_charge=dispatch.battery_charge,
            battery_discharge=dispatch.battery_discharge,
            served_critical_load=Energy(value.served_critical, Unit.KILOWATT_HOUR),
            served_noncritical_load=Energy(
                value.served_noncritical,
                Unit.KILOWATT_HOUR,
            ),
            critical_unserved_load=dispatch.critical_unserved_load,
            noncritical_unserved_load=dispatch.noncritical_unserved_load,
            other_conversion_loss=dispatch.other_conversion_loss,
            storage_conversion_loss=Energy(value.storage_loss, Unit.KILOWATT_HOUR),
            state_of_charge_start=Energy(
                value.state_of_charge_start,
                Unit.KILOWATT_HOUR,
            ),
            state_of_charge_end=Energy(
                value.state_of_charge_end,
                Unit.KILOWATT_HOUR,
            ),
            constraint_check_passed=False,
        )
