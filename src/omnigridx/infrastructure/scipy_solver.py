"""SciPy implementation of the in-process bounded MILP solver port."""

from decimal import Decimal
from time import perf_counter
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp  # type: ignore[import-untyped]

from omnigridx.application.optimization import MilpModel, MilpSolution
from omnigridx.domain.values import FiniteNumber


class ScipyMilpSolver:
    def solve(self, model: MilpModel) -> MilpSolution:
        started = perf_counter()
        constraints = LinearConstraint(
            np.asarray(
                [[float(value) for value in row.coefficients] for row in model.constraints],
                dtype=float,
            ),
            np.asarray(
                [
                    -np.inf if row.lower_bound is None else float(row.lower_bound)
                    for row in model.constraints
                ],
                dtype=float,
            ),
            np.asarray(
                [
                    np.inf if row.upper_bound is None else float(row.upper_bound)
                    for row in model.constraints
                ],
                dtype=float,
            ),
        )
        raw: Any = milp(
            c=np.asarray([float(value) for value in model.objective], dtype=float),
            integrality=np.asarray(model.integrality, dtype=int),
            bounds=Bounds(
                np.asarray([float(value) for value in model.lower_bounds], dtype=float),
                np.asarray([float(value) for value in model.upper_bounds], dtype=float),
            ),
            constraints=constraints,
            options={"presolve": True},
        )
        elapsed = Decimal(str(perf_counter() - started))
        raw_values = getattr(raw, "x", None)
        values = (
            tuple(Decimal(str(float(value))) for value in raw_values)
            if raw_values is not None
            else None
        )
        objective = getattr(raw, "fun", None)
        gap = getattr(raw, "mip_gap", None)
        bound = getattr(raw, "mip_dual_bound", None)
        return MilpSolution(
            status_code=int(raw.status),
            message=str(raw.message),
            values=values,
            objective_value=Decimal(str(float(objective))) if objective is not None else None,
            runtime_seconds=FiniteNumber(elapsed),
            optimality_gap=FiniteNumber(Decimal(str(float(gap)))) if gap is not None else None,
            best_bound=Decimal(str(float(bound))) if bound is not None else None,
        )
