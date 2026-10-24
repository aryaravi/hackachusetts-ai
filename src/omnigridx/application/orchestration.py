"""All-or-nothing orchestration for the bundled three-alternative comparison."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from omnigridx.domain.constraints import ConstraintChecker, ConstraintReport
from omnigridx.domain.records import AlternativeType, RunManifest, Schedule
from omnigridx.domain.simulation import SimulationRequest
from omnigridx.domain.values import FiniteNumber, Identifier, Power, Unit

from .costing import SampleCostCalculator, SampleScreeningRateConfiguration, ScreeningCost
from .dispatch import ExistingDispatch, RuleBasedDispatch
from .metrics import (
    CleanEnergyAttribution,
    CleanEnergyShare,
    EmissionsFactor,
    PurchasedElectricityEmissions,
    calculate_clean_energy_share,
    calculate_purchased_electricity_emissions,
)
from .optimization import CostMinimizingOptimizer, OptimizationCosts, OptimizationOutcome
from .outage import OutageDeclaration, OutageMetricsCalculator, OutageServiceMetrics


@dataclass(frozen=True, slots=True)
class AlternativeMetrics:
    alternative: AlternativeType
    schedule: Schedule
    operating_cost: ScreeningCost
    outage_service: OutageServiceMetrics
    purchased_electricity_emissions: PurchasedElectricityEmissions
    clean_energy_share: CleanEnergyShare
    peak_import: Power
    critical_service_fraction: FiniteNumber | None
    solver_outcome: OptimizationOutcome | None
    checker_report: ConstraintReport


@dataclass(frozen=True, slots=True)
class ThreeAlternativeComparison:
    manifest: RunManifest
    alternatives: tuple[AlternativeMetrics, AlternativeMetrics, AlternativeMetrics]
    recommendation: None = None


class OrchestrationError(RuntimeError):
    """The complete three-alternative comparison could not be published."""


CleanEnergyAttributionProvider = Callable[[Schedule], Sequence[CleanEnergyAttribution]]


class RunOrchestrator:
    """Run and publish exactly three checked alternatives, or publish nothing."""

    def __init__(
        self,
        checker: ConstraintChecker,
        optimizer: CostMinimizingOptimizer,
    ) -> None:
        self._checker = checker
        self._optimizer = optimizer

    def run(
        self,
        manifest: RunManifest,
        scenario: SimulationRequest,
        optimization_costs: OptimizationCosts,
        rate_configuration: SampleScreeningRateConfiguration,
        outage: OutageDeclaration | None,
        emissions_factor: EmissionsFactor,
        clean_energy_attributions: CleanEnergyAttributionProvider,
    ) -> ThreeAlternativeComparison:
        self._validate_shared_inputs(
            manifest, scenario, optimization_costs, rate_configuration
        )

        existing = ExistingDispatch(self._checker).run(scenario)
        rule_based = RuleBasedDispatch(self._checker).run(scenario)
        optimized_request = replace(
            scenario,
            schedule_id=Identifier(f"{manifest.identifier.value}-optimized"),
            alternative_type=AlternativeType.OPTIMIZED,
        )
        solver_outcome = self._optimizer.optimize(
            optimized_request, optimization_costs, existing
        )
        if solver_outcome.schedule is None:
            raise OrchestrationError(
                f"optimized alternative unavailable: {solver_outcome.status.value}"
            )

        schedules = (existing, rule_based, solver_outcome.schedule)
        results: list[AlternativeMetrics] = []
        for schedule in schedules:
            checked_request = replace(
                scenario,
                schedule_id=schedule.identifier,
                alternative_type=schedule.alternative_type,
            )
            checker_report = self._checker.check(checked_request, schedule)
            if checker_report.checked_schedule is None:
                raise OrchestrationError(
                    f"{schedule.alternative_type.value} alternative failed independent checking"
                )
            checked_schedule = checker_report.checked_schedule
            results.append(
                self._metrics(
                    checked_request,
                    checked_schedule,
                    rate_configuration,
                    outage,
                    emissions_factor,
                    clean_energy_attributions(checked_schedule),
                    solver_outcome
                    if schedule.alternative_type is AlternativeType.OPTIMIZED
                    else None,
                    checker_report,
                )
            )

        return ThreeAlternativeComparison(
            manifest=manifest,
            alternatives=(results[0], results[1], results[2]),
        )

    @staticmethod
    def _validate_shared_inputs(
        manifest: RunManifest,
        scenario: SimulationRequest,
        optimization_costs: OptimizationCosts,
        rate_configuration: SampleScreeningRateConfiguration,
    ) -> None:
        interval_ids = tuple(item.interval.identifier for item in scenario.intervals)
        if (
            scenario.scenario_version_id != manifest.scenario_version_id
            or interval_ids != manifest.ordered_interval_ids
        ):
            raise ValueError("scenario must match the bundled run manifest")
        if manifest.tariff_configuration.version != rate_configuration.version:
            raise ValueError("sample rate configuration must match the run manifest")
        if len(optimization_costs.interval_rates) != len(interval_ids) or any(
            rate.import_rate_per_kwh != rate_configuration.import_rate_per_kwh
            or rate.export_credit_per_kwh != rate_configuration.export_credit_per_kwh
            for rate in optimization_costs.interval_rates
        ):
            raise ValueError("optimization and reporting must use the same sample rates")

    @staticmethod
    def _metrics(
        scenario: SimulationRequest,
        schedule: Schedule,
        rate_configuration: SampleScreeningRateConfiguration,
        outage: OutageDeclaration | None,
        emissions_factor: EmissionsFactor,
        attributions: Sequence[CleanEnergyAttribution],
        solver_outcome: OptimizationOutcome | None,
        checker_report: ConstraintReport,
    ) -> AlternativeMetrics:
        duration_by_id = {
            item.interval.identifier: item.interval.duration.value
            for item in scenario.intervals
        }
        peak_import = max(
            (
                item.grid_import.value / duration_by_id[item.interval_id]
                for item in schedule.intervals
            ),
            default=Decimal(0),
        )
        critical_demand = sum(
            (item.critical_load.value for item in scenario.intervals), Decimal(0)
        )
        served_critical = sum(
            (item.served_critical_load.value for item in schedule.intervals), Decimal(0)
        )
        return AlternativeMetrics(
            alternative=schedule.alternative_type,
            schedule=schedule,
            operating_cost=SampleCostCalculator().calculate(
                schedule.intervals, rate_configuration
            ),
            outage_service=OutageMetricsCalculator().calculate(
                scenario, schedule, outage
            ),
            purchased_electricity_emissions=calculate_purchased_electricity_emissions(
                schedule.intervals, emissions_factor
            ),
            clean_energy_share=calculate_clean_energy_share(schedule, attributions),
            peak_import=Power(peak_import, Unit.KILOWATT),
            critical_service_fraction=(
                None
                if critical_demand == 0
                else FiniteNumber(served_critical / critical_demand)
            ),
            solver_outcome=solver_outcome,
            checker_report=checker_report,
        )
