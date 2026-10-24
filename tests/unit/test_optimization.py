from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from omnigridx.application import (
    CostMinimizingOptimizer,
    IntervalCostRate,
    MilpModel,
    MilpSolution,
    OptimizationCosts,
    OptimizationStatus,
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
from omnigridx.infrastructure import ScipyMilpSolver


def energy(value: str | int) -> Energy:
    return Energy(Decimal(value), Unit.KILOWATT_HOUR)


def power(value: str | int) -> Power:
    return Power(Decimal(value), Unit.KILOWATT)


def interval(identifier: str, hour: int, generation: int) -> SimulationIntervalInput:
    return SimulationIntervalInput(
        interval=Interval(
            Identifier(identifier),
            Timestamp(datetime(2026, 1, 1, hour, tzinfo=UTC)),
            Duration(1, Unit.HOUR),
        ),
        generation_available=energy(generation),
        generation_asset_available=True,
        battery_available=True,
        critical_load=energy(1),
        noncritical_load=energy(0),
        grid=GridIntervalLimit(True, True, True, power(5), power(5)),
        dispatch=IntervalDispatch(
            energy(0), energy(0), energy(0), energy(0), energy(0), energy(0), energy(0), energy(0)
        ),
    )


def optimization_request() -> SimulationRequest:
    return SimulationRequest(
        run_id=Identifier("run-optimized"),
        schedule_id=Identifier("schedule-optimized"),
        scenario_version_id=Identifier("scenario-1"),
        alternative_type=AlternativeType.OPTIMIZED,
        intervals=(interval("low-cost", 0, 2), interval("high-cost", 1, 0)),
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
            reserve_mode=ReserveMode.UNAVAILABLE_FOR_NORMAL_DISPATCH,
        ),
        minimum_critical_service_fraction=FiniteNumber(1),
    )


def optimization_costs() -> OptimizationCosts:
    return OptimizationCosts(
        currency="USD",
        interval_rates=(
            IntervalCostRate(FiniteNumber(1), FiniteNumber(0)),
            IntervalCostRate(FiniteNumber(10), FiniteNumber(0)),
        ),
        battery_degradation_per_kwh_throughput=FiniteNumber(Decimal("0.1")),
        critical_unserved_penalty_per_kwh=FiniteNumber(100),
        noncritical_unserved_penalty_per_kwh=FiniteNumber(100),
    )


def checker() -> ConstraintChecker:
    tolerance = energy("0.000001")
    return ConstraintChecker(
        ConstraintTolerances("2026.1", tolerance, tolerance, tolerance, tolerance)
    )


def completed_simulation(request: SimulationRequest) -> Schedule:
    baseline_intervals = (
        replace(
            request.intervals[0],
            dispatch=replace(
                request.intervals[0].dispatch,
                generation_dispatched=energy(1),
            ),
        ),
        replace(
            request.intervals[1],
            dispatch=replace(request.intervals[1].dispatch, grid_import=energy(1)),
        ),
    )
    return SimulationEngine().simulate(
        replace(
            request,
            schedule_id=Identifier("completed-simulation"),
            alternative_type=AlternativeType.EXISTING,
            intervals=baseline_intervals,
        )
    )


def test_scipy_milp_finds_the_enumerated_optimum_and_publishes_checked_schedule() -> None:
    request = optimization_request()
    costs = optimization_costs()
    optimizer = CostMinimizingOptimizer(ScipyMilpSolver(), checker())

    model = optimizer.build_model(request, costs)
    result = optimizer.optimize(request, costs, completed_simulation(request))

    assert all(bound.is_finite() for bound in model.upper_bounds)
    assert sum(model.integrality) == 4  # grid and battery direction for each interval
    assert result.status is OptimizationStatus.OPTIMAL
    assert result.schedule is not None
    assert result.objective is not None
    assert result.checker_report is not None
    assert tuple(value.battery_charge for value in result.schedule.intervals) == (
        energy(1),
        energy(0),
    )
    assert tuple(value.battery_discharge for value in result.schedule.intervals) == (
        energy(0),
        energy(1),
    )
    assert tuple(value.grid_import for value in result.schedule.intervals) == (
        energy(0),
        energy(0),
    )
    enumerated_costs = tuple(
        Decimal(10) * (Decimal(1) - stored) + Decimal("0.2") * stored
        for stored in (Decimal(0), Decimal(1))
    )
    assert result.objective.total.value == min(enumerated_costs) == Decimal("0.2")
    assert result.solver_status_code == 0
    assert result.checker_report.passed
    assert all(value.constraint_check_passed for value in result.schedule.intervals)


class StubSolver:
    def __init__(self, status_code: int, candidate: str | None) -> None:
        self.status_code = status_code
        self.candidate = candidate
        self.calls = 0

    def solve(self, model: MilpModel) -> MilpSolution:
        self.calls += 1
        values = None
        if self.candidate == "valid":
            values = (
                Decimal(2), Decimal(0), Decimal(0), Decimal(1),
                Decimal(0), Decimal(0), Decimal(0), Decimal(1),
                Decimal(0), Decimal(0), Decimal(0), Decimal(0),
                Decimal(1), Decimal(0), Decimal(0), Decimal(0),
            ) + (Decimal(0),) * (len(model.variable_names) - 16)
        elif self.candidate == "invalid":
            values = (Decimal(0),) * len(model.variable_names)
        return MilpSolution(
            status_code=self.status_code,
            message=f"stub status {self.status_code}",
            values=values,
            objective_value=Decimal("0.2") if values is not None else None,
            runtime_seconds=FiniteNumber(Decimal("0.5")),
            optimality_gap=(
                FiniteNumber(Decimal("0.05")) if self.status_code == 1 else None
            ),
            best_bound=Decimal("0.1") if values is not None else None,
        )


@pytest.mark.parametrize(
    ("status_code", "candidate", "expected_status", "published"),
    (
        (0, "valid", OptimizationStatus.OPTIMAL, True),
        (1, "valid", OptimizationStatus.FEASIBLE_AT_TIMEOUT, True),
        (1, None, OptimizationStatus.TIMEOUT_WITHOUT_SOLUTION, False),
        (2, None, OptimizationStatus.PROVEN_INFEASIBLE, False),
        (4, None, OptimizationStatus.NUMERICAL_FAILURE, False),
        (0, "invalid", OptimizationStatus.CONSTRAINT_CHECK_FAILED, False),
    ),
)
def test_solver_outcomes_map_status_and_publication_fields(
    status_code: int,
    candidate: str | None,
    expected_status: OptimizationStatus,
    published: bool,
) -> None:
    request = optimization_request()
    solver = StubSolver(status_code, candidate)
    result = CostMinimizingOptimizer(solver, checker()).optimize(
        request, optimization_costs(), completed_simulation(request)
    )

    assert result.status is expected_status
    assert (result.schedule is not None) is published
    assert (result.objective is not None) is published
    assert result.solver_status_code == status_code
    assert result.solver_message == f"stub status {status_code}"
    assert result.runtime_seconds == FiniteNumber(Decimal("0.5"))
    assert (result.checker_report is not None) is (
        published or expected_status is OptimizationStatus.CONSTRAINT_CHECK_FAILED
    )


def test_optimization_rejects_missing_completed_simulation_before_solving() -> None:
    request = optimization_request()
    solver = StubSolver(0, "valid")
    optimizer = CostMinimizingOptimizer(solver, checker())

    with pytest.raises(ValueError, match="requires a completed simulation"):
        optimizer.optimize(request, optimization_costs(), None)

    assert solver.calls == 0
