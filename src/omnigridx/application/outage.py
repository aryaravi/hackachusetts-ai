"""Deterministic outage-service metrics for completed sample schedules."""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from enum import StrEnum

from omnigridx.domain.records import Schedule
from omnigridx.domain.simulation import SimulationRequest
from omnigridx.domain.values import Duration, Energy, Timestamp, Unit

OUTAGE_SERVICE_LABEL = "Outage_Service_Screening"
OUTAGE_SERVICE_DISCLOSURE = (
    "Deterministic outage-service screening; not probabilistic reliability analysis."
)


class OutageServiceStatus(StrEnum):
    EVALUATED = "evaluated"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True, slots=True)
class OutageDeclaration:
    start: Timestamp | None
    duration: Duration | None


@dataclass(frozen=True, slots=True)
class OutageServiceMetrics:
    status: OutageServiceStatus
    critical_unserved_energy: Energy | None
    interruption_duration: Duration | None
    label: str = OUTAGE_SERVICE_LABEL
    disclosure: str = OUTAGE_SERVICE_DISCLOSURE


class OutageServiceError(ValueError):
    """An outage evaluation rejected with all independently detectable issues."""

    def __init__(self, issues: tuple[str, ...]) -> None:
        self.issues = issues
        super().__init__("; ".join(issues))


class OutageMetricsCalculator:
    """Calculate deterministic critical-load outcomes for a declared outage."""

    def calculate(
        self,
        scenario: SimulationRequest,
        schedule: Schedule,
        outage: OutageDeclaration | None,
    ) -> OutageServiceMetrics:
        if outage is None and all(
            item.grid.available and item.grid.import_limit is None
            for item in scenario.intervals
        ):
            return OutageServiceMetrics(
                status=OutageServiceStatus.NOT_EVALUATED,
                critical_unserved_energy=None,
                interruption_duration=None,
            )

        missing: list[str] = []
        if outage is None or outage.start is None:
            missing.append("outage_start")
        if outage is None or outage.duration is None:
            missing.append("outage_duration")
        elif outage.duration.value <= 0:
            missing.append("outage_duration_must_be_positive")
        if not scenario.intervals:
            missing.extend(
                (
                    "interval_grid_availability",
                    "critical_load_profile",
                    "equipment_availability",
                    "interval_import_bounds",
                )
            )
        if scenario.battery is None:
            missing.extend(("starting_state_of_charge", "reserve_behavior"))
        if missing:
            raise OutageServiceError(tuple(missing))

        assert outage is not None and outage.start is not None and outage.duration is not None
        outage_end = outage.start.instant_utc + timedelta(hours=float(outage.duration.value))
        outage_inputs = tuple(
            item
            for item in scenario.intervals
            if item.interval.start.instant_utc < outage_end
            and item.interval.end_utc > outage.start.instant_utc
        )
        issues: list[str] = []
        if not outage_inputs:
            issues.append("outage_period_matches_no_scenario_interval")

        outage_ids = {item.interval.identifier for item in outage_inputs}
        for item in scenario.intervals:
            in_outage = item.interval.identifier in outage_ids
            if in_outage and item.grid.available:
                issues.append(f"grid_must_be_unavailable:{item.interval.identifier}")
            elif not in_outage and not item.grid.available:
                issues.append(f"grid_unavailability_outside_declared_outage:{item.interval.identifier}")

        expected_ids = tuple(item.interval.identifier for item in scenario.intervals)
        result_ids = tuple(item.interval_id for item in schedule.intervals)
        if schedule.scenario_version_id != scenario.scenario_version_id or result_ids != expected_ids:
            issues.append("completed_schedule_must_match_scenario_intervals")
        elif not all(item.constraint_check_passed for item in schedule.intervals):
            issues.append("completed_schedule_must_pass_constraint_checks")
        else:
            results = {item.interval_id: item for item in schedule.intervals}
            for interval_id in outage_ids:
                result = results[interval_id]
                if result.grid_import.value != 0 or result.grid_export.value != 0:
                    issues.append(f"grid_bounds_must_be_zero_while_unavailable:{interval_id}")

        if issues:
            raise OutageServiceError(tuple(issues))

        results = {item.interval_id: item for item in schedule.intervals}
        critical_unserved = sum(
            (results[item.interval.identifier].critical_unserved_load.value for item in outage_inputs),
            Decimal(0),
        )
        interruption_duration = sum(
            (
                item.interval.duration.value
                for item in outage_inputs
                if results[item.interval.identifier].critical_unserved_load.value > 0
            ),
            Decimal(0),
        )
        return OutageServiceMetrics(
            status=OutageServiceStatus.EVALUATED,
            critical_unserved_energy=Energy(critical_unserved, Unit.KILOWATT_HOUR),
            interruption_duration=Duration(interruption_duration, Unit.HOUR),
        )
