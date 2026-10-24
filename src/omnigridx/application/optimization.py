"""Bounded cost-minimizing dispatch with independent candidate validation."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from omnigridx.domain.constraints import ConstraintChecker, ConstraintReport
from omnigridx.domain.records import AlternativeType, IntervalResult, Schedule
from omnigridx.domain.simulation import (
    BatterySpec,
    ReserveMode,
    SimulationIntervalInput,
    SimulationRequest,
    TerminalTreatmentKind,
)
from omnigridx.domain.values import Energy, FiniteNumber, Money, Unit

from .ports import SolverPort


@dataclass(frozen=True, slots=True)
class LinearConstraintRow:
    coefficients: tuple[Decimal, ...]
    lower_bound: Decimal | None
    upper_bound: Decimal | None


@dataclass(frozen=True, slots=True)
class MilpModel:
    variable_names: tuple[str, ...]
    objective: tuple[Decimal, ...]
    lower_bounds: tuple[Decimal, ...]
    upper_bounds: tuple[Decimal, ...]
    integrality: tuple[int, ...]
    constraints: tuple[LinearConstraintRow, ...]

    def __post_init__(self) -> None:
        size = len(self.variable_names)
        if not size or any(
            len(values) != size
            for values in (
                self.objective,
                self.lower_bounds,
                self.upper_bounds,
                self.integrality,
            )
        ):
            raise ValueError("MILP variable vectors must have one value per variable")
        if any(len(row.coefficients) != size for row in self.constraints):
            raise ValueError("MILP constraint rows must match the variable count")
        if any(lower > upper for lower, upper in zip(self.lower_bounds, self.upper_bounds)):
            raise ValueError("MILP lower bounds cannot exceed upper bounds")
        if any(value not in (0, 1) for value in self.integrality):
            raise ValueError("MILP integrality values must be zero or one")


@dataclass(frozen=True, slots=True)
class MilpSolution:
    status_code: int
    message: str
    values: tuple[Decimal, ...] | None
    objective_value: Decimal | None
    runtime_seconds: FiniteNumber
    optimality_gap: FiniteNumber | None
    best_bound: Decimal | None


@dataclass(frozen=True, slots=True)
class IntervalCostRate:
    import_rate_per_kwh: FiniteNumber
    export_credit_per_kwh: FiniteNumber

    def __post_init__(self) -> None:
        if self.import_rate_per_kwh.value < 0 or self.export_credit_per_kwh.value < 0:
            raise ValueError("interval import rates and export credits must be nonnegative")


@dataclass(frozen=True, slots=True)
class OptimizationCosts:
    currency: str
    interval_rates: tuple[IntervalCostRate, ...]
    battery_degradation_per_kwh_throughput: FiniteNumber
    critical_unserved_penalty_per_kwh: FiniteNumber
    noncritical_unserved_penalty_per_kwh: FiniteNumber

    def __post_init__(self) -> None:
        if not self.currency or self.currency != self.currency.strip():
            raise ValueError("optimization currency must be a nonempty trimmed string")
        if any(
            value.value < 0
            for value in (
                self.battery_degradation_per_kwh_throughput,
                self.critical_unserved_penalty_per_kwh,
                self.noncritical_unserved_penalty_per_kwh,
            )
        ):
            raise ValueError("optimization costs and penalties must be nonnegative")


@dataclass(frozen=True, slots=True)
class ObjectiveComponents:
    operating_cost: Money
    degradation_cost: Money
    critical_unserved_penalty: Money
    noncritical_unserved_penalty: Money
    terminal_energy_term: Money
    total: Money


class OptimizationStatus(StrEnum):
    OPTIMAL = "optimal"
    FEASIBLE_AT_TIMEOUT = "feasible_at_timeout"
    TIMEOUT_WITHOUT_SOLUTION = "timeout_without_solution"
    PROVEN_INFEASIBLE = "proven_infeasible"
    NUMERICAL_FAILURE = "numerical_failure"
    CONSTRAINT_CHECK_FAILED = "constraint_check_failed"


@dataclass(frozen=True, slots=True)
class OptimizationOutcome:
    status: OptimizationStatus
    schedule: Schedule | None
    objective: ObjectiveComponents | None
    solver_status_code: int
    solver_message: str
    runtime_seconds: FiniteNumber
    optimality_gap: FiniteNumber | None
    best_bound: Money | None
    checker_report: ConstraintReport | None


OptimizedCandidate = OptimizationOutcome


class OptimizationError(RuntimeError):
    def __init__(
        self,
        message: str,
        solver_solution: MilpSolution,
        checker_report: ConstraintReport | None = None,
    ) -> None:
        self.solver_solution = solver_solution
        self.checker_report = checker_report
        super().__init__(message)


class CostMinimizingOptimizer:
    """Build and solve one physical MILP, publishing only a checked schedule."""

    _VARIABLES_PER_INTERVAL = 8
    _GENERATION = 0
    _IMPORT = 1
    _EXPORT = 2
    _CHARGE = 3
    _DISCHARGE = 4
    _CRITICAL_UNSERVED = 5
    _NONCRITICAL_UNSERVED = 6
    _SOC = 7

    def __init__(
        self,
        solver: SolverPort[MilpModel, MilpSolution],
        checker: ConstraintChecker,
    ) -> None:
        self._solver = solver
        self._checker = checker

    def optimize(
        self,
        request: SimulationRequest,
        costs: OptimizationCosts,
        completed_simulation: Schedule | None,
    ) -> OptimizationOutcome:
        self._require_completed_simulation(request, completed_simulation)
        model = self.build_model(request, costs)
        solution = self._solver.solve(model)
        best_bound = (
            Money(solution.best_bound, Unit.US_DOLLAR)
            if solution.best_bound is not None
            else None
        )

        if solution.status_code == 2:
            return self._outcome(OptimizationStatus.PROVEN_INFEASIBLE, solution, best_bound)
        if solution.status_code == 1 and (
            solution.values is None or solution.objective_value is None
        ):
            return self._outcome(
                OptimizationStatus.TIMEOUT_WITHOUT_SOLUTION, solution, best_bound
            )
        if solution.status_code not in (0, 1):
            return self._outcome(OptimizationStatus.NUMERICAL_FAILURE, solution, best_bound)
        if solution.values is None or solution.objective_value is None:
            return self._outcome(OptimizationStatus.NUMERICAL_FAILURE, solution, best_bound)
        if len(solution.values) != len(model.variable_names):
            return self._outcome(OptimizationStatus.NUMERICAL_FAILURE, solution, best_bound)

        candidate = self._schedule(request, solution.values)
        checker_report = self._checker.check(request, candidate)
        if checker_report.checked_schedule is None:
            return self._outcome(
                OptimizationStatus.CONSTRAINT_CHECK_FAILED,
                solution,
                best_bound,
                checker_report,
            )

        schedule = checker_report.checked_schedule
        return OptimizationOutcome(
            status=(
                OptimizationStatus.OPTIMAL
                if solution.status_code == 0
                else OptimizationStatus.FEASIBLE_AT_TIMEOUT
            ),
            schedule=schedule,
            objective=self._objective(schedule, request.battery, costs),
            solver_status_code=solution.status_code,
            solver_message=solution.message,
            runtime_seconds=solution.runtime_seconds,
            optimality_gap=solution.optimality_gap,
            best_bound=best_bound,
            checker_report=checker_report,
        )

    @staticmethod
    def _require_completed_simulation(
        request: SimulationRequest,
        completed_simulation: Schedule | None,
    ) -> None:
        expected_ids = tuple(item.interval.identifier for item in request.intervals)
        if (
            completed_simulation is None
            or completed_simulation.scenario_version_id != request.scenario_version_id
            or tuple(item.interval_id for item in completed_simulation.intervals)
            != expected_ids
        ):
            raise ValueError("optimization requires a completed simulation")

    @staticmethod
    def _outcome(
        status: OptimizationStatus,
        solution: MilpSolution,
        best_bound: Money | None,
        checker_report: ConstraintReport | None = None,
    ) -> OptimizationOutcome:
        return OptimizationOutcome(
            status=status,
            schedule=None,
            objective=None,
            solver_status_code=solution.status_code,
            solver_message=solution.message,
            runtime_seconds=solution.runtime_seconds,
            optimality_gap=solution.optimality_gap,
            best_bound=best_bound,
            checker_report=checker_report,
        )

    def build_model(self, request: SimulationRequest, costs: OptimizationCosts) -> MilpModel:
        battery = self._validate_request(request, costs)
        count = len(request.intervals)
        variable_names: list[str] = []
        objective: list[Decimal] = []
        lower_bounds: list[Decimal] = []
        upper_bounds: list[Decimal] = []
        integrality: list[int] = []

        import_bounds: list[Decimal] = []
        export_bounds: list[Decimal] = []
        charge_bounds: list[Decimal] = []
        discharge_bounds: list[Decimal] = []
        soc_lower_bounds: list[Decimal] = []

        for index, item in enumerate(request.intervals):
            duration = item.interval.duration.value
            charge_bound = battery.charge_limit.value * duration if item.battery_available else Decimal(0)
            discharge_bound = battery.discharge_limit.value * duration if item.battery_available else Decimal(0)
            generation_bound = item.generation_available.value if item.generation_asset_available else Decimal(0)
            import_bound = self._grid_bound(item, True, charge_bound, discharge_bound)
            export_bound = self._grid_bound(item, False, charge_bound, discharge_bound)
            next_floor = (
                self._reserve_floor(battery, request.intervals[index + 1].grid.available)
                if index + 1 < count
                else battery.minimum_soc.value
            )
            soc_floor = max(self._reserve_floor(battery, item.grid.available), next_floor)

            import_bounds.append(import_bound)
            export_bounds.append(export_bound)
            charge_bounds.append(charge_bound)
            discharge_bounds.append(discharge_bound)
            soc_lower_bounds.append(soc_floor)

            rate = costs.interval_rates[index]
            variable_names.extend(
                f"{name}[{item.interval.identifier}]"
                for name in (
                    "generation",
                    "grid_import",
                    "grid_export",
                    "battery_charge",
                    "battery_discharge",
                    "critical_unserved",
                    "noncritical_unserved",
                    "soc_end",
                )
            )
            objective.extend(
                (
                    Decimal(0),
                    rate.import_rate_per_kwh.value,
                    -rate.export_credit_per_kwh.value,
                    costs.battery_degradation_per_kwh_throughput.value,
                    costs.battery_degradation_per_kwh_throughput.value,
                    costs.critical_unserved_penalty_per_kwh.value,
                    costs.noncritical_unserved_penalty_per_kwh.value,
                    Decimal(0),
                )
            )
            lower_bounds.extend((Decimal(0),) * 7 + (soc_floor,))
            upper_bounds.extend(
                (
                    generation_bound,
                    import_bound,
                    export_bound,
                    charge_bound,
                    discharge_bound,
                    item.critical_load.value,
                    item.noncritical_load.value,
                    battery.maximum_soc.value,
                )
            )
            integrality.extend((0,) * self._VARIABLES_PER_INTERVAL)

        terminal = battery.terminal_treatment
        if terminal.kind is TerminalTreatmentKind.VALUE:
            assert terminal.value_per_kwh is not None
            objective[self._index(count - 1, self._SOC)] -= terminal.value_per_kwh.value

        grid_binary: list[int | None] = []
        battery_binary: list[int | None] = []
        for index, item in enumerate(request.intervals):
            grid_binary.append(
                self._binary(
                    variable_names,
                    objective,
                    lower_bounds,
                    upper_bounds,
                    integrality,
                    f"grid_direction[{item.interval.identifier}]",
                )
                if not request.simultaneous_grid_flows_allowed
                and import_bounds[index] > 0
                and export_bounds[index] > 0
                else None
            )
            battery_binary.append(
                self._binary(
                    variable_names,
                    objective,
                    lower_bounds,
                    upper_bounds,
                    integrality,
                    f"battery_direction[{item.interval.identifier}]",
                )
                if not request.simultaneous_battery_flows_allowed
                and charge_bounds[index] > 0
                and discharge_bounds[index] > 0
                else None
            )

        rows: list[tuple[dict[int, Decimal], Decimal | None, Decimal | None]] = []
        for index, item in enumerate(request.intervals):
            base = index * self._VARIABLES_PER_INTERVAL
            total_load_and_loss = (
                item.critical_load.value
                + item.noncritical_load.value
                + item.dispatch.other_conversion_loss.value
            )
            rows.append(
                (
                    {
                        base + self._GENERATION: Decimal(1),
                        base + self._IMPORT: Decimal(1),
                        base + self._DISCHARGE: Decimal(1),
                        base + self._CRITICAL_UNSERVED: Decimal(1),
                        base + self._NONCRITICAL_UNSERVED: Decimal(1),
                        base + self._CHARGE: Decimal(-1),
                        base + self._EXPORT: Decimal(-1),
                    },
                    total_load_and_loss,
                    total_load_and_loss,
                )
            )
            soc_coefficients = {
                base + self._SOC: Decimal(1),
                base + self._CHARGE: -battery.charge_efficiency.value,
                base + self._DISCHARGE: Decimal(1) / battery.discharge_efficiency.value,
            }
            soc_rhs = battery.initial_soc.value if index == 0 else Decimal(0)
            if index > 0:
                soc_coefficients[self._index(index - 1, self._SOC)] = Decimal(-1)
            rows.append((soc_coefficients, soc_rhs, soc_rhs))

            required_critical = self._required_critical_service(request, item)
            rows.append(
                (
                    {base + self._CRITICAL_UNSERVED: Decimal(1)},
                    None,
                    item.critical_load.value - required_critical,
                )
            )

            grid_direction = grid_binary[index]
            if grid_direction is not None:
                rows.extend(
                    (
                        (
                            {
                                base + self._IMPORT: Decimal(1),
                                grid_direction: -import_bounds[index],
                            },
                            None,
                            Decimal(0),
                        ),
                        (
                            {
                                base + self._EXPORT: Decimal(1),
                                grid_direction: export_bounds[index],
                            },
                            None,
                            export_bounds[index],
                        ),
                    )
                )
            storage_direction = battery_binary[index]
            if storage_direction is not None:
                rows.extend(
                    (
                        (
                            {
                                base + self._CHARGE: Decimal(1),
                                storage_direction: -charge_bounds[index],
                            },
                            None,
                            Decimal(0),
                        ),
                        (
                            {
                                base + self._DISCHARGE: Decimal(1),
                                storage_direction: discharge_bounds[index],
                            },
                            None,
                            discharge_bounds[index],
                        ),
                    )
                )

        target = terminal.target_soc
        if terminal.kind is TerminalTreatmentKind.MINIMUM:
            assert target is not None
            rows.append(({self._index(count - 1, self._SOC): Decimal(1)}, target.value, None))
        elif terminal.kind is TerminalTreatmentKind.EQUALITY:
            assert target is not None
            rows.append(
                ({self._index(count - 1, self._SOC): Decimal(1)}, target.value, target.value)
            )

        size = len(variable_names)
        constraints = tuple(
            LinearConstraintRow(
                tuple(coefficients.get(index, Decimal(0)) for index in range(size)),
                lower,
                upper,
            )
            for coefficients, lower, upper in rows
        )
        return MilpModel(
            tuple(variable_names),
            tuple(objective),
            tuple(lower_bounds),
            tuple(upper_bounds),
            tuple(integrality),
            constraints,
        )

    @staticmethod
    def _validate_request(
        request: SimulationRequest,
        costs: OptimizationCosts,
    ) -> BatterySpec:
        if request.alternative_type is not AlternativeType.OPTIMIZED:
            raise ValueError("optimization requires the optimized alternative type")
        if not request.intervals:
            raise ValueError("optimization requires at least one interval")
        if len(costs.interval_rates) != len(request.intervals):
            raise ValueError("optimization requires one cost rate per interval")
        battery = request.battery
        if battery is None:
            raise ValueError("optimization requires a battery specification")
        first_floor = CostMinimizingOptimizer._reserve_floor(
            battery, request.intervals[0].grid.available
        )
        if battery.initial_soc.value < first_floor:
            raise ValueError("initial SOC is below the active reserve floor")
        terminal = battery.terminal_treatment
        if (
            terminal.kind is TerminalTreatmentKind.VALUE
            and terminal.currency != costs.currency
        ):
            raise ValueError("terminal value currency must match optimization currency")
        return battery

    @staticmethod
    def _grid_bound(
        item: SimulationIntervalInput,
        importing: bool,
        charge_bound: Decimal,
        discharge_bound: Decimal,
    ) -> Decimal:
        allowed = item.grid.import_allowed if importing else item.grid.export_allowed
        limit = item.grid.import_limit if importing else item.grid.export_limit
        if not item.grid.available or not allowed:
            return Decimal(0)
        duration = item.interval.duration.value
        if importing:
            physical = (
                item.critical_load.value
                + item.noncritical_load.value
                + charge_bound
                + item.dispatch.other_conversion_loss.value
            )
        else:
            physical = (
                item.generation_available.value
                if item.generation_asset_available
                else Decimal(0)
            ) + discharge_bound
        return physical if limit is None else min(physical, limit.value * duration)

    @staticmethod
    def _reserve_floor(battery: BatterySpec, grid_available: bool) -> Decimal:
        if battery.reserve_mode is ReserveMode.UNAVAILABLE_FOR_NORMAL_DISPATCH:
            return max(battery.minimum_soc.value, battery.reserve.value)
        if battery.reserve_mode is ReserveMode.OUTAGE_RELEASABLE and grid_available:
            return max(battery.minimum_soc.value, battery.reserve.value)
        return battery.minimum_soc.value

    @staticmethod
    def _required_critical_service(
        request: SimulationRequest,
        item: SimulationIntervalInput,
    ) -> Decimal:
        fraction = request.minimum_critical_service_fraction
        if fraction is not None:
            return item.critical_load.value * fraction.value
        quantity = request.minimum_critical_service_quantity
        assert quantity is not None
        return quantity.value

    @staticmethod
    def _binary(
        names: list[str],
        objective: list[Decimal],
        lower_bounds: list[Decimal],
        upper_bounds: list[Decimal],
        integrality: list[int],
        name: str,
    ) -> int:
        index = len(names)
        names.append(name)
        objective.append(Decimal(0))
        lower_bounds.append(Decimal(0))
        upper_bounds.append(Decimal(1))
        integrality.append(1)
        return index

    @classmethod
    def _index(cls, interval: int, variable: int) -> int:
        return interval * cls._VARIABLES_PER_INTERVAL + variable

    @classmethod
    def _schedule(
        cls,
        request: SimulationRequest,
        values: tuple[Decimal, ...],
    ) -> Schedule:
        battery = request.battery
        assert battery is not None
        intervals: list[IntervalResult] = []
        previous_soc = battery.initial_soc.value
        for index, item in enumerate(request.intervals):
            base = index * cls._VARIABLES_PER_INTERVAL
            generation = max(Decimal(0), values[base + cls._GENERATION])
            grid_import = max(Decimal(0), values[base + cls._IMPORT])
            grid_export = max(Decimal(0), values[base + cls._EXPORT])
            charge = max(Decimal(0), values[base + cls._CHARGE])
            discharge = max(Decimal(0), values[base + cls._DISCHARGE])
            critical_unserved = max(Decimal(0), values[base + cls._CRITICAL_UNSERVED])
            noncritical_unserved = max(Decimal(0), values[base + cls._NONCRITICAL_UNSERVED])
            state_of_charge = values[base + cls._SOC]
            storage_loss = (
                (Decimal(1) - battery.charge_efficiency.value) * charge
                + (Decimal(1) / battery.discharge_efficiency.value - Decimal(1))
                * discharge
            )
            intervals.append(
                IntervalResult(
                    run_id=request.run_id,
                    alternative_type=request.alternative_type,
                    interval_id=item.interval.identifier,
                    generation_available=item.generation_available,
                    generation_dispatched=Energy(generation, Unit.KILOWATT_HOUR),
                    generation_curtailed=Energy(
                        max(Decimal(0), item.generation_available.value - generation),
                        Unit.KILOWATT_HOUR,
                    ),
                    grid_import=Energy(grid_import, Unit.KILOWATT_HOUR),
                    grid_export=Energy(grid_export, Unit.KILOWATT_HOUR),
                    battery_charge=Energy(charge, Unit.KILOWATT_HOUR),
                    battery_discharge=Energy(discharge, Unit.KILOWATT_HOUR),
                    served_critical_load=Energy(
                        max(Decimal(0), item.critical_load.value - critical_unserved),
                        Unit.KILOWATT_HOUR,
                    ),
                    served_noncritical_load=Energy(
                        max(Decimal(0), item.noncritical_load.value - noncritical_unserved),
                        Unit.KILOWATT_HOUR,
                    ),
                    critical_unserved_load=Energy(
                        critical_unserved, Unit.KILOWATT_HOUR
                    ),
                    noncritical_unserved_load=Energy(
                        noncritical_unserved, Unit.KILOWATT_HOUR
                    ),
                    other_conversion_loss=item.dispatch.other_conversion_loss,
                    storage_conversion_loss=Energy(storage_loss, Unit.KILOWATT_HOUR),
                    state_of_charge_start=Energy(previous_soc, Unit.KILOWATT_HOUR),
                    state_of_charge_end=Energy(state_of_charge, Unit.KILOWATT_HOUR),
                    constraint_check_passed=False,
                )
            )
            previous_soc = state_of_charge
        return Schedule(
            identifier=request.schedule_id,
            scenario_version_id=request.scenario_version_id,
            alternative_type=request.alternative_type,
            intervals=tuple(intervals),
        )

    @staticmethod
    def _objective(
        schedule: Schedule,
        battery: BatterySpec | None,
        costs: OptimizationCosts,
    ) -> ObjectiveComponents:
        assert battery is not None
        operating = sum(
            (
                interval.grid_import.value * rate.import_rate_per_kwh.value
                - interval.grid_export.value * rate.export_credit_per_kwh.value
                for interval, rate in zip(schedule.intervals, costs.interval_rates)
            ),
            Decimal(0),
        )
        degradation = sum(
            (
                (interval.battery_charge.value + interval.battery_discharge.value)
                * costs.battery_degradation_per_kwh_throughput.value
                for interval in schedule.intervals
            ),
            Decimal(0),
        )
        critical_penalty = sum(
            (
                interval.critical_unserved_load.value
                * costs.critical_unserved_penalty_per_kwh.value
                for interval in schedule.intervals
            ),
            Decimal(0),
        )
        noncritical_penalty = sum(
            (
                interval.noncritical_unserved_load.value
                * costs.noncritical_unserved_penalty_per_kwh.value
                for interval in schedule.intervals
            ),
            Decimal(0),
        )
        terminal = Decimal(0)
        treatment = battery.terminal_treatment
        if treatment.kind is TerminalTreatmentKind.VALUE:
            assert treatment.value_per_kwh is not None
            terminal = -schedule.intervals[-1].state_of_charge_end.value * treatment.value_per_kwh.value
        total = operating + degradation + critical_penalty + noncritical_penalty + terminal
        return ObjectiveComponents(
            Money(operating, Unit.US_DOLLAR),
            Money(degradation, Unit.US_DOLLAR),
            Money(critical_penalty, Unit.US_DOLLAR),
            Money(noncritical_penalty, Unit.US_DOLLAR),
            Money(terminal, Unit.US_DOLLAR),
            Money(total, Unit.US_DOLLAR),
        )
