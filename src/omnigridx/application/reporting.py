"""Stable report model and transport-neutral serialization."""

from dataclasses import dataclass, field
from decimal import Decimal
import hashlib
import json
from typing import Any

from omnigridx.domain.records import IntervalResult

from .orchestration import AlternativeMetrics, ThreeAlternativeComparison

REPORT_SCHEMA_VERSION = "fast-judge-mvp-v1"
REPORT_LABEL = "Fast_Judge_MVP"
REPORT_ASSUMPTIONS = (
    "Bundled synthetic Massachusetts commercial-site sample only.",
    "Sample rates and emissions factors are screening assumptions.",
    "Optimization is constrained grid intelligence over declared sample inputs.",
)
REPORT_EXCLUSIONS = (
    "No verified tariff or historical bill reconciliation.",
    "No customer data or customer-data upload.",
    "No local-grid, feeder-capacity, interconnection, or power-flow feasibility conclusion.",
    "No probabilistic reliability conclusion.",
    "No AI, weather, or demand forecasting.",
)
REPORT_DISCLOSURES = (
    "Every cost and savings value is a sample-only Screening_Estimate.",
    "Outage results are deterministic Outage_Service_Screening, not probabilistic reliability.",
    "The optimized alternative uses constrained grid intelligence; it is not autonomous control.",
)


def _decimal(value: Decimal) -> str:
    normalized = value.normalize()
    return "0" if normalized == 0 else format(normalized, "f")


def _quantity(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    return {"value": _decimal(value.value), "unit": value.unit.value}


def _interval(value: IntervalResult) -> dict[str, Any]:
    return {
        "interval_id": str(value.interval_id),
        "generation_available": _quantity(value.generation_available),
        "generation_dispatched": _quantity(value.generation_dispatched),
        "generation_curtailed": _quantity(value.generation_curtailed),
        "grid_import": _quantity(value.grid_import),
        "grid_export": _quantity(value.grid_export),
        "battery_charge": _quantity(value.battery_charge),
        "battery_discharge": _quantity(value.battery_discharge),
        "served_critical_load": _quantity(value.served_critical_load),
        "served_noncritical_load": _quantity(value.served_noncritical_load),
        "critical_unserved_load": _quantity(value.critical_unserved_load),
        "noncritical_unserved_load": _quantity(value.noncritical_unserved_load),
        "other_conversion_loss": _quantity(value.other_conversion_loss),
        "storage_conversion_loss": _quantity(value.storage_conversion_loss),
        "state_of_charge_start": _quantity(value.state_of_charge_start),
        "state_of_charge_end": _quantity(value.state_of_charge_end),
        "constraint_check_passed": value.constraint_check_passed,
    }


def _alternative(value: AlternativeMetrics) -> dict[str, Any]:
    cost = value.operating_cost
    outage = value.outage_service
    emissions = value.purchased_electricity_emissions
    clean = value.clean_energy_share
    solver = value.solver_outcome
    objective = solver.objective if solver is not None else None
    return {
        "alternative": value.alternative.value,
        "schedule": {
            "id": str(value.schedule.identifier),
            "scenario_version_id": str(value.schedule.scenario_version_id),
            "intervals": [_interval(item) for item in value.schedule.intervals],
        },
        "metrics": {
            "operating_cost": {
                "label": cost.operating_cost.label,
                "amount": _quantity(cost.operating_cost.amount),
                "gross_import": _quantity(cost.gross_import),
                "gross_export": _quantity(cost.gross_export),
                "import_charge": _quantity(cost.import_charge.amount),
                "export_credit": _quantity(cost.export_credit.amount),
                "rate_configuration": {
                    "id": str(cost.rate_configuration.identifier),
                    "version": cost.rate_configuration.version,
                    "effective_period": [
                        date.isoformat() for date in cost.rate_configuration.effective_period
                    ],
                    "currency": cost.rate_configuration.currency.value,
                    "units": cost.rate_configuration.units,
                    "source_or_assumption": cost.rate_configuration.source_or_assumption_label,
                    "exclusions": list(cost.rate_configuration.exclusions),
                },
                "disclaimer": cost.disclaimer,
            },
            "outage_service": {
                "status": outage.status.value,
                "label": outage.label,
                "critical_unserved_energy": _quantity(outage.critical_unserved_energy),
                "interruption_duration": _quantity(outage.interruption_duration),
                "disclosure": outage.disclosure,
            },
            "purchased_electricity_emissions": {
                "name": emissions.name,
                "estimate": _quantity(emissions.estimate),
                "gross_import": _quantity(emissions.gross_import),
                "gross_export_reported_separately": _quantity(emissions.gross_export),
                "factor": {
                    "value": _decimal(emissions.factor.value.value),
                    "units": f"{emissions.factor.numerator_unit}/{emissions.factor.denominator_unit}",
                    "geography": emissions.factor.geography,
                    "data_year": emissions.factor.data_year,
                    "version": emissions.factor.version,
                    "included_gases": list(emissions.factor.included_gases),
                    "intended_purpose": emissions.factor.intended_purpose,
                    "source": emissions.factor.source,
                    "classification": emissions.factor.classification,
                },
                "exclusions": list(emissions.exclusions),
            },
            "clean_energy_share": {
                "qualifying_energy": _quantity(clean.qualifying_energy),
                "served_load": _quantity(clean.served_load),
                "share": None if clean.share is None else _decimal(clean.share.value),
            },
            "peak_import": _quantity(value.peak_import),
            "critical_service_fraction": (
                None
                if value.critical_service_fraction is None
                else _decimal(value.critical_service_fraction.value)
            ),
        },
        "solver": {
            "status": "not_applicable" if solver is None else solver.status.value,
            "status_code": None if solver is None else solver.solver_status_code,
            "optimality_gap": (
                None
                if solver is None or solver.optimality_gap is None
                else _decimal(solver.optimality_gap.value)
            ),
            "objective": (
                None
                if objective is None
                else {
                    "operating_cost": _quantity(objective.operating_cost),
                    "degradation_cost": _quantity(objective.degradation_cost),
                    "critical_unserved_penalty": _quantity(objective.critical_unserved_penalty),
                    "noncritical_unserved_penalty": _quantity(objective.noncritical_unserved_penalty),
                    "terminal_energy_term": _quantity(objective.terminal_energy_term),
                    "total": _quantity(objective.total),
                }
            ),
        },
        "independent_checker": {
            "status": "passed" if value.checker_report.passed else "failed",
            "tolerance_version": value.checker_report.tolerance_version,
            "diagnostics": [item.constraint for item in value.checker_report.diagnostics],
        },
    }


@dataclass(frozen=True, slots=True)
class JudgeReport:
    sample_id: str
    comparison: ThreeAlternativeComparison
    assumptions: tuple[str, ...] = field(default=REPORT_ASSUMPTIONS, init=False)
    exclusions: tuple[str, ...] = field(default=REPORT_EXCLUSIONS, init=False)
    disclosures: tuple[str, ...] = field(default=REPORT_DISCLOSURES, init=False)
    schema_version: str = field(default=REPORT_SCHEMA_VERSION, init=False)
    label: str = field(default=REPORT_LABEL, init=False)

    def __post_init__(self) -> None:
        if not self.sample_id.strip():
            raise ValueError("sample identity is required")
        alternatives = tuple(item.alternative for item in self.comparison.alternatives)
        if alternatives != self.comparison.manifest.alternative_types:
            raise ValueError("report requires the manifest's exactly three alternatives")
        if any(not item.checker_report.passed for item in self.comparison.alternatives):
            raise ValueError("report requires independently checked alternatives")

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "label": self.label,
            "sample_id": self.sample_id,
            "manifest": {
                **self.comparison.manifest.canonical_dict(),
                "fingerprint": str(self.comparison.manifest.fingerprint),
            },
            "alternatives": [_alternative(item) for item in self.comparison.alternatives],
            "recommendation": self.comparison.recommendation,
            "assumptions": list(self.assumptions),
            "exclusions": list(self.exclusions),
            "disclosures": list(self.disclosures),
        }

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            self.canonical_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**self.canonical_dict(), "report_fingerprint": self.fingerprint}

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
