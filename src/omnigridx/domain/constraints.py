"""Independent post-simulation validation for candidate schedules."""

from dataclasses import dataclass, replace
from decimal import Decimal

from .records import IntervalResult, Schedule
from .simulation import (
    BatterySpec,
    ReserveMode,
    SimulationIntervalInput,
    SimulationRequest,
    TerminalTreatmentKind,
)
from .values import Energy, Identifier, Unit


@dataclass(frozen=True, slots=True)
class ConstraintTolerances:
    """Versioned absolute kWh tolerances by constraint class."""

    version: str
    conservation: Energy
    decomposition: Energy
    bounds: Energy
    state: Energy

    def __post_init__(self) -> None:
        if not self.version or self.version != self.version.strip():
            raise ValueError("constraint tolerance version must be a nonempty trimmed string")


@dataclass(frozen=True, slots=True)
class ConstraintDiagnostic:
    interval_id: Identifier | None
    constraint: str
    residual: Energy | None
    tolerance: Energy | None
    message: str


@dataclass(frozen=True, slots=True)
class ConstraintReport:
    tolerance_version: str
    diagnostics: tuple[ConstraintDiagnostic, ...]
    checked_schedule: Schedule | None

    @property
    def passed(self) -> bool:
        return self.checked_schedule is not None


class ConstraintChecker:
    """Recompute hard constraints without using simulation or solver checks."""

    def __init__(self, tolerances: ConstraintTolerances) -> None:
        self._tolerances = tolerances

    def check(self, request: SimulationRequest, candidate: Schedule) -> ConstraintReport:
        diagnostics: list[ConstraintDiagnostic] = []
        battery = request.battery
        if battery is None:
            self._structural(
                diagnostics,
                None,
                "missing_input",
                "battery specification is required",
            )
            return self._report(candidate, diagnostics)

        if candidate.scenario_version_id != request.scenario_version_id:
            self._structural(
                diagnostics,
                None,
                "scenario_identity",
                "candidate scenario version does not match the checked request",
            )
        if candidate.alternative_type is not request.alternative_type:
            self._structural(
                diagnostics,
                None,
                "alternative_identity",
                "candidate alternative does not match the checked request",
            )

        expected_ids = tuple(item.interval.identifier for item in request.intervals)
        if len(set(expected_ids)) != len(expected_ids):
            self._structural(
                diagnostics,
                None,
                "interval_cardinality",
                "request interval identifiers must be unique",
            )
        actual_by_id = {value.interval_id: value for value in candidate.intervals}
        expected_set = set(expected_ids)
        for interval_id in expected_ids:
            if interval_id not in actual_by_id:
                self._structural(
                    diagnostics,
                    interval_id,
                    "interval_cardinality",
                    "candidate is missing the required interval",
                )
        for interval_id in actual_by_id.keys() - expected_set:
            self._structural(
                diagnostics,
                interval_id,
                "interval_cardinality",
                "candidate contains an interval outside the horizon",
            )

        previous_soc: Decimal | None = battery.initial_soc.value
        for item in request.intervals:
            interval_id = item.interval.identifier
            result = actual_by_id.get(interval_id)
            if result is None:
                previous_soc = None
                continue
            self._check_interval(
                diagnostics,
                request,
                battery,
                item,
                result,
                previous_soc,
            )
            previous_soc = result.state_of_charge_end.value

        if request.intervals:
            final_result = actual_by_id.get(request.intervals[-1].interval.identifier)
            if final_result is not None:
                self._check_terminal(
                    diagnostics,
                    battery,
                    final_result.interval_id,
                    final_result.state_of_charge_end.value,
                )

        return self._report(candidate, diagnostics)

    def _check_interval(
        self,
        diagnostics: list[ConstraintDiagnostic],
        request: SimulationRequest,
        battery: BatterySpec,
        item: SimulationIntervalInput,
        result: IntervalResult,
        previous_soc: Decimal | None,
    ) -> None:
        interval_id = item.interval.identifier
        decomposition_tolerance = self._tolerances.decomposition
        bound_tolerance = self._tolerances.bounds
        state_tolerance = self._tolerances.state

        if result.run_id != request.run_id or result.alternative_type is not request.alternative_type:
            self._structural(
                diagnostics,
                interval_id,
                "result_identity",
                "interval result run or alternative does not match the checked request",
            )

        self._equal(
            diagnostics,
            interval_id,
            "generation_available",
            result.generation_available.value,
            item.generation_available.value,
            decomposition_tolerance,
        )
        self._equal(
            diagnostics,
            interval_id,
            "generation_decomposition",
            result.generation_dispatched.value + result.generation_curtailed.value,
            result.generation_available.value,
            decomposition_tolerance,
        )
        generation_bound = (
            item.generation_available.value
            if item.generation_asset_available
            else Decimal(0)
        )
        self._at_most(
            diagnostics,
            interval_id,
            "generation_dispatch",
            result.generation_dispatched.value,
            generation_bound,
            bound_tolerance,
        )
        self._equal(
            diagnostics,
            interval_id,
            "critical_load_decomposition",
            result.served_critical_load.value + result.critical_unserved_load.value,
            item.critical_load.value,
            decomposition_tolerance,
        )
        self._equal(
            diagnostics,
            interval_id,
            "noncritical_load_decomposition",
            result.served_noncritical_load.value + result.noncritical_unserved_load.value,
            item.noncritical_load.value,
            decomposition_tolerance,
        )

        duration = item.interval.duration.value
        import_bound = self._grid_bound(
            item.grid.available,
            item.grid.import_allowed,
            item.grid.import_limit.value if item.grid.import_limit is not None else None,
            duration,
        )
        export_bound = self._grid_bound(
            item.grid.available,
            item.grid.export_allowed,
            item.grid.export_limit.value if item.grid.export_limit is not None else None,
            duration,
        )
        self._at_most(
            diagnostics,
            interval_id,
            "grid_import_bound",
            result.grid_import.value,
            import_bound,
            bound_tolerance,
        )
        self._at_most(
            diagnostics,
            interval_id,
            "grid_export_bound",
            result.grid_export.value,
            export_bound,
            bound_tolerance,
        )
        if not request.simultaneous_grid_flows_allowed:
            self._at_most(
                diagnostics,
                interval_id,
                "grid_direction",
                min(result.grid_import.value, result.grid_export.value),
                Decimal(0),
                bound_tolerance,
            )

        charge_bound = battery.charge_limit.value * duration
        discharge_bound = battery.discharge_limit.value * duration
        if not item.battery_available:
            charge_bound = discharge_bound = Decimal(0)
        self._at_most(
            diagnostics,
            interval_id,
            "battery_charge_bound",
            result.battery_charge.value,
            charge_bound,
            bound_tolerance,
        )
        self._at_most(
            diagnostics,
            interval_id,
            "battery_discharge_bound",
            result.battery_discharge.value,
            discharge_bound,
            bound_tolerance,
        )
        if not request.simultaneous_battery_flows_allowed:
            self._at_most(
                diagnostics,
                interval_id,
                "battery_direction",
                min(result.battery_charge.value, result.battery_discharge.value),
                Decimal(0),
                bound_tolerance,
            )

        if previous_soc is not None:
            self._equal(
                diagnostics,
                interval_id,
                "state_of_charge_start",
                result.state_of_charge_start.value,
                previous_soc,
                state_tolerance,
            )
        expected_end_soc = (
            result.state_of_charge_start.value
            + battery.charge_efficiency.value * result.battery_charge.value
            - result.battery_discharge.value / battery.discharge_efficiency.value
        )
        self._equal(
            diagnostics,
            interval_id,
            "state_of_charge_transition",
            result.state_of_charge_end.value,
            expected_end_soc,
            state_tolerance,
        )
        expected_storage_loss = (
            (Decimal(1) - battery.charge_efficiency.value) * result.battery_charge.value
            + (Decimal(1) / battery.discharge_efficiency.value - Decimal(1))
            * result.battery_discharge.value
        )
        self._equal(
            diagnostics,
            interval_id,
            "storage_conversion_loss",
            result.storage_conversion_loss.value,
            expected_storage_loss,
            state_tolerance,
        )
        reserve_floor = self._reserve_floor(battery, item.grid.available)
        for suffix, soc in (
            ("start", result.state_of_charge_start.value),
            ("end", result.state_of_charge_end.value),
        ):
            self._at_least(
                diagnostics,
                interval_id,
                f"state_of_charge_{suffix}_bound",
                soc,
                reserve_floor,
                bound_tolerance,
            )
            self._at_most(
                diagnostics,
                interval_id,
                f"state_of_charge_{suffix}_bound",
                soc,
                battery.maximum_soc.value,
                bound_tolerance,
            )

        fraction = request.minimum_critical_service_fraction
        required_critical = (
            item.critical_load.value * fraction.value
            if fraction is not None
            else request.minimum_critical_service_quantity.value
            if request.minimum_critical_service_quantity is not None
            else Decimal("Infinity")
        )
        self._at_least(
            diagnostics,
            interval_id,
            "critical_service",
            result.served_critical_load.value,
            required_critical,
            bound_tolerance,
        )

        supply = (
            result.generation_dispatched.value
            + result.grid_import.value
            + result.battery_discharge.value
        )
        use = (
            result.served_critical_load.value
            + result.served_noncritical_load.value
            + result.battery_charge.value
            + result.grid_export.value
            + result.other_conversion_loss.value
        )
        self._equal(
            diagnostics,
            interval_id,
            "energy_conservation",
            supply,
            use,
            self._tolerances.conservation,
        )

    def _check_terminal(
        self,
        diagnostics: list[ConstraintDiagnostic],
        battery: BatterySpec,
        interval_id: Identifier,
        final_soc: Decimal,
    ) -> None:
        treatment = battery.terminal_treatment
        target = treatment.target_soc
        if treatment.kind is TerminalTreatmentKind.MINIMUM and target is not None:
            self._at_least(
                diagnostics,
                interval_id,
                "terminal_soc",
                final_soc,
                target.value,
                self._tolerances.state,
            )
        elif treatment.kind is TerminalTreatmentKind.EQUALITY and target is not None:
            self._equal(
                diagnostics,
                interval_id,
                "terminal_soc",
                final_soc,
                target.value,
                self._tolerances.state,
            )

    def _report(
        self,
        candidate: Schedule,
        diagnostics: list[ConstraintDiagnostic],
    ) -> ConstraintReport:
        checked_schedule = None
        if not diagnostics:
            checked_schedule = replace(
                candidate,
                intervals=tuple(
                    replace(value, constraint_check_passed=True)
                    for value in candidate.intervals
                ),
            )
        return ConstraintReport(
            tolerance_version=self._tolerances.version,
            diagnostics=tuple(diagnostics),
            checked_schedule=checked_schedule,
        )

    @staticmethod
    def _grid_bound(
        available: bool,
        allowed: bool,
        limit_kw: Decimal | None,
        duration_hours: Decimal,
    ) -> Decimal | None:
        if not available or not allowed:
            return Decimal(0)
        return None if limit_kw is None else limit_kw * duration_hours

    @staticmethod
    def _reserve_floor(battery: BatterySpec, grid_available: bool) -> Decimal:
        if battery.reserve_mode is ReserveMode.UNAVAILABLE_FOR_NORMAL_DISPATCH:
            return max(battery.minimum_soc.value, battery.reserve.value)
        if battery.reserve_mode is ReserveMode.OUTAGE_RELEASABLE and grid_available:
            return max(battery.minimum_soc.value, battery.reserve.value)
        return battery.minimum_soc.value

    @staticmethod
    def _structural(
        diagnostics: list[ConstraintDiagnostic],
        interval_id: Identifier | None,
        constraint: str,
        message: str,
    ) -> None:
        diagnostics.append(
            ConstraintDiagnostic(interval_id, constraint, None, None, message)
        )

    @staticmethod
    def _equal(
        diagnostics: list[ConstraintDiagnostic],
        interval_id: Identifier,
        constraint: str,
        actual: Decimal,
        expected: Decimal,
        tolerance: Energy,
    ) -> None:
        residual = abs(actual - expected)
        if residual > tolerance.value:
            diagnostics.append(
                ConstraintDiagnostic(
                    interval_id,
                    constraint,
                    Energy(residual, Unit.KILOWATT_HOUR),
                    tolerance,
                    f"residual {residual} kWh exceeds {tolerance.value} kWh",
                )
            )

    @staticmethod
    def _at_most(
        diagnostics: list[ConstraintDiagnostic],
        interval_id: Identifier,
        constraint: str,
        actual: Decimal,
        maximum: Decimal | None,
        tolerance: Energy,
    ) -> None:
        if maximum is None:
            return
        residual = actual - maximum
        if residual > tolerance.value:
            diagnostics.append(
                ConstraintDiagnostic(
                    interval_id,
                    constraint,
                    Energy(residual, Unit.KILOWATT_HOUR),
                    tolerance,
                    f"upper-bound residual {residual} kWh exceeds {tolerance.value} kWh",
                )
            )

    @staticmethod
    def _at_least(
        diagnostics: list[ConstraintDiagnostic],
        interval_id: Identifier,
        constraint: str,
        actual: Decimal,
        minimum: Decimal,
        tolerance: Energy,
    ) -> None:
        residual = minimum - actual
        if residual > tolerance.value:
            diagnostics.append(
                ConstraintDiagnostic(
                    interval_id,
                    constraint,
                    Energy(residual, Unit.KILOWATT_HOUR),
                    tolerance,
                    f"lower-bound residual {residual} kWh exceeds {tolerance.value} kWh",
                )
            )
