"""Transparent sample-only operating-cost calculation."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Sequence

from omnigridx.domain.records import IntervalResult
from omnigridx.domain.values import Energy, FiniteNumber, Identifier, Money, Unit

SCREENING_ESTIMATE_LABEL = "Screening_Estimate"
SAMPLE_RATE_DISCLAIMER = (
    "This Sample_Screening_Rate_Configuration is not a verified tariff, "
    "historical bill reconciliation, account-applicability determination, "
    "or future-savings validation."
)


@dataclass(frozen=True, slots=True)
class SampleScreeningRateConfiguration:
    identifier: Identifier
    version: str
    effective_period: tuple[date, date]
    import_rate_per_kwh: FiniteNumber
    export_credit_per_kwh: FiniteNumber
    currency: Unit
    source_or_assumption_label: str
    exclusions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.version or self.version != self.version.strip():
            raise ValueError("rate configuration version must be nonempty")
        if self.effective_period[0] > self.effective_period[1]:
            raise ValueError("rate configuration effective period is invalid")
        if self.import_rate_per_kwh.value < 0 or self.export_credit_per_kwh.value < 0:
            raise ValueError("sample rates and export credits must be nonnegative")
        if self.currency is not Unit.US_DOLLAR:
            raise ValueError("sample rate configuration currency must be USD")
        if not self.source_or_assumption_label.strip():
            raise ValueError("source or assumption label must be nonempty")
        if not self.exclusions or any(not item.strip() for item in self.exclusions):
            raise ValueError("sample rate configuration exclusions must be nonempty")

    @property
    def units(self) -> str:
        return f"{self.currency.value}/{Unit.KILOWATT_HOUR.value}"


@dataclass(frozen=True, slots=True)
class ScreeningEstimate:
    amount: Money
    label: str = field(default=SCREENING_ESTIMATE_LABEL, init=False)


@dataclass(frozen=True, slots=True)
class ScreeningCost:
    gross_import: Energy
    gross_export: Energy
    import_charge: ScreeningEstimate
    export_credit: ScreeningEstimate
    operating_cost: ScreeningEstimate
    rate_configuration: SampleScreeningRateConfiguration
    disclaimer: str = field(default=SAMPLE_RATE_DISCLAIMER, init=False)


BUNDLED_SAMPLE_RATE_CONFIGURATION = SampleScreeningRateConfiguration(
    identifier=Identifier("bundled-ma-sample-screening-rate"),
    version="2026.1",
    effective_period=(date(2026, 1, 1), date(2026, 12, 31)),
    import_rate_per_kwh=FiniteNumber(Decimal("0.25")),
    export_credit_per_kwh=FiniteNumber(Decimal("0.08")),
    currency=Unit.US_DOLLAR,
    source_or_assumption_label="Bundled sample assumption; not a utility tariff",
    exclusions=("demand charges", "fixed charges", "taxes and riders"),
)


class SampleCostCalculator:
    """Apply a disclosed sample rate to gross interval grid flows."""

    def calculate(
        self,
        intervals: Sequence[IntervalResult],
        config: SampleScreeningRateConfiguration,
    ) -> ScreeningCost:
        gross_import = sum((item.grid_import.value for item in intervals), Decimal(0))
        gross_export = sum((item.grid_export.value for item in intervals), Decimal(0))
        import_charge = gross_import * config.import_rate_per_kwh.value
        export_credit = gross_export * config.export_credit_per_kwh.value

        return ScreeningCost(
            gross_import=Energy(gross_import, Unit.KILOWATT_HOUR),
            gross_export=Energy(gross_export, Unit.KILOWATT_HOUR),
            import_charge=ScreeningEstimate(Money(import_charge, config.currency)),
            export_credit=ScreeningEstimate(Money(export_credit, config.currency)),
            operating_cost=ScreeningEstimate(
                Money(import_charge - export_credit, config.currency)
            ),
            rate_configuration=config,
        )
