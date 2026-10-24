"""Build the in-memory judge report from one versioned bundled sample."""

from datetime import datetime
from decimal import Decimal
import hashlib
from importlib.resources import files
import json
from typing import Any, cast

from omnigridx.application.costing import BUNDLED_SAMPLE_RATE_CONFIGURATION
from omnigridx.application.metrics import CleanEnergyAttribution, EmissionsFactor
from omnigridx.application.optimization import (
    CostMinimizingOptimizer,
    IntervalCostRate,
    OptimizationCosts,
)
from omnigridx.application.orchestration import RunOrchestrator
from omnigridx.application.outage import OutageDeclaration
from omnigridx.application.reporting import JudgeReport
from omnigridx.domain.constraints import ConstraintChecker, ConstraintTolerances
from omnigridx.domain.records import (
    AlternativeType,
    ManifestDecimal,
    NamedHash,
    RunManifest,
    Schedule,
    Sha256Digest,
    VersionReference,
)
from omnigridx.domain.simulation import (
    BatterySpec,
    GridIntervalLimit,
    IntervalDispatch,
    ReserveMode,
    SimulationIntervalInput,
    SimulationRequest,
    TerminalTreatment,
    TerminalTreatmentKind,
)
from omnigridx.domain.values import (
    CapabilityStatus,
    Duration,
    Energy,
    FiniteNumber,
    Identifier,
    Interval,
    Power,
    Timestamp,
    Unit,
)

from .scipy_solver import ScipyMilpSolver

SAMPLE_DATASET_ID = "massachusetts-commercial-site-sample-v1"
_SAMPLE_PATH = "data/sample/judge-scenario-v1.json"


def _energy(value: str | int | Decimal) -> Energy:
    return Energy(Decimal(value), Unit.KILOWATT_HOUR)


def _power(value: str | int) -> Power:
    return Power(Decimal(value), Unit.KILOWATT)


def _timestamp(value: str) -> Timestamp:
    return Timestamp(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _sample_bytes() -> bytes:
    return files("omnigridx.infrastructure").joinpath(_SAMPLE_PATH).read_bytes()


def _sample() -> tuple[bytes, dict[str, Any]]:
    raw = _sample_bytes()
    return raw, cast(dict[str, Any], json.loads(raw))


def _scenario(data: dict[str, Any]) -> SimulationRequest:
    intervals: list[SimulationIntervalInput] = []
    for source in data["intervals"]:
        dispatch = source["existing_dispatch"]
        intervals.append(
            SimulationIntervalInput(
                interval=Interval(
                    Identifier(source["id"]),
                    _timestamp(source["start"]),
                    Duration(Decimal(source["duration_hours"]), Unit.HOUR),
                ),
                generation_available=_energy(source["generation_available_kwh"]),
                generation_asset_available=True,
                battery_available=True,
                critical_load=_energy(source["critical_load_kwh"]),
                noncritical_load=_energy(source["noncritical_load_kwh"]),
                grid=GridIntervalLimit(
                    source["grid_available"], True, True, _power(2), _power(2)
                ),
                dispatch=IntervalDispatch(
                    _energy(dispatch["generation_dispatched_kwh"]),
                    _energy(dispatch["grid_import_kwh"]),
                    _energy(dispatch["grid_export_kwh"]),
                    _energy(dispatch["battery_charge_kwh"]),
                    _energy(dispatch["battery_discharge_kwh"]),
                    _energy(dispatch["critical_unserved_kwh"]),
                    _energy(dispatch["noncritical_unserved_kwh"]),
                    _energy(0),
                ),
            )
        )
    battery = data["battery"]
    return SimulationRequest(
        run_id=Identifier("sample-run"),
        schedule_id=Identifier("sample-template"),
        scenario_version_id=Identifier(data["scenario_version_id"]),
        alternative_type=AlternativeType.EXISTING,
        intervals=tuple(intervals),
        battery=BatterySpec(
            usable_capacity=_energy(battery["usable_capacity_kwh"]),
            minimum_soc=_energy(battery["minimum_soc_kwh"]),
            maximum_soc=_energy(battery["maximum_soc_kwh"]),
            charge_limit=_power(battery["charge_limit_kw"]),
            discharge_limit=_power(battery["discharge_limit_kw"]),
            charge_efficiency=FiniteNumber(Decimal(battery["charge_efficiency"])),
            discharge_efficiency=FiniteNumber(Decimal(battery["discharge_efficiency"])),
            initial_soc=_energy(battery["initial_soc_kwh"]),
            terminal_treatment=TerminalTreatment(
                TerminalTreatmentKind.MINIMUM, target_soc=_energy(0)
            ),
            reserve=_energy(battery["reserve_kwh"]),
            reserve_mode=ReserveMode.OUTAGE_RELEASABLE,
        ),
        minimum_critical_service_fraction=FiniteNumber(0),
    )


def _attributions(schedule: Schedule) -> tuple[CleanEnergyAttribution, ...]:
    values: list[CleanEnergyAttribution] = []
    for interval in schedule.intervals:
        served = interval.served_critical_load.value + interval.served_noncritical_load.value
        direct = max(
            Decimal(0),
            interval.generation_dispatched.value
            - interval.battery_charge.value
            - interval.grid_export.value,
        )
        values.append(
            CleanEnergyAttribution(
                interval.interval_id,
                _energy(min(served, direct)),
                interval.battery_discharge,
            )
        )
    return tuple(values)


def build_sample_report(deployment_mode: str) -> JudgeReport:
    if deployment_mode not in {"demo-local", "demo-public"}:
        raise ValueError("sample report supports demo-local or demo-public only")
    raw, data = _sample()
    if data.get("sample_id") != SAMPLE_DATASET_ID:
        raise ValueError("bundled sample identity does not match the approved dataset")
    scenario = _scenario(data)
    tolerance = _energy("0.000001")
    checker = ConstraintChecker(
        ConstraintTolerances("2026.1", tolerance, tolerance, tolerance, tolerance)
    )
    rate = BUNDLED_SAMPLE_RATE_CONFIGURATION
    manifest = RunManifest(
        identifier=Identifier("bundled-manifest-v1"),
        scenario_version_id=scenario.scenario_version_id,
        created_at=_timestamp(data["created_at"]),
        alternative_types=tuple(AlternativeType),
        ordered_interval_ids=tuple(item.interval.identifier for item in scenario.intervals),
        input_hashes=(
            NamedHash("judge-scenario-v1", Sha256Digest(hashlib.sha256(raw).hexdigest())),
        ),
        source_record_ids=(Identifier("bundled-synthetic-sample-v1"),),
        pack=VersionReference("Massachusetts_Data_Pack", "2026.1"),
        policy_snapshot=VersionReference("none", "sample"),
        tariff_configuration=VersionReference(rate.identifier.value, rate.version),
        calculation_code=VersionReference("omnigridx", "0.1.0"),
        dependencies=(VersionReference("scipy", "1.15.1"),),
        solver=VersionReference("scipy-milp", "1.15.1"),
        solver_settings=(ManifestDecimal("presolve", FiniteNumber(1), "boolean"),),
        tolerances=(
            ManifestDecimal(
                "energy_balance", FiniteNumber(Decimal("0.000001")), "kWh"
            ),
        ),
        random_seed=0,
        deployment_mode=deployment_mode,
        capability_mode=CapabilityStatus.HACKATHON_DEMO,
    )
    optimization_costs = OptimizationCosts(
        currency="USD",
        interval_rates=tuple(
            IntervalCostRate(rate.import_rate_per_kwh, rate.export_credit_per_kwh)
            for _ in scenario.intervals
        ),
        battery_degradation_per_kwh_throughput=FiniteNumber(Decimal("0.01")),
        critical_unserved_penalty_per_kwh=FiniteNumber(100),
        noncritical_unserved_penalty_per_kwh=FiniteNumber(100),
    )
    factor = data["emissions_factor"]
    emissions_factor = EmissionsFactor(
        value=FiniteNumber(Decimal(factor["kg_co2e_per_kwh"])),
        numerator_unit=Unit.KILOGRAM_CO2E.value,
        denominator_unit=Unit.KILOWATT_HOUR.value,
        geography=factor["geography"],
        data_year=factor["data_year"],
        version=factor["version"],
        included_gases=("CO2", "CH4", "N2O"),
        intended_purpose="sample screening",
        source=factor["source"],
        classification="average sample assumption",
    )
    outage = data["outage"]
    comparison = RunOrchestrator(
        checker, CostMinimizingOptimizer(ScipyMilpSolver(), checker)
    ).run(
        manifest,
        scenario,
        optimization_costs,
        rate,
        OutageDeclaration(
            _timestamp(outage["start"]),
            Duration(Decimal(outage["duration_hours"]), Unit.HOUR),
        ),
        emissions_factor,
        _attributions,
    )
    return JudgeReport(SAMPLE_DATASET_ID, comparison)
