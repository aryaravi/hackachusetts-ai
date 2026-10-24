"""Purchased-electricity emissions and origin-aware clean-energy metrics."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from omnigridx.domain.records import IntervalResult, Schedule
from omnigridx.domain.values import Emissions, Energy, FiniteNumber, Identifier, Unit


@dataclass(frozen=True, slots=True)
class EmissionsFactor:
    value: FiniteNumber
    numerator_unit: str
    denominator_unit: str
    geography: str
    data_year: int
    version: str
    included_gases: tuple[str, ...]
    intended_purpose: str
    source: str
    classification: str

    def __post_init__(self) -> None:
        if self.value.value < 0:
            raise ValueError("emissions factor must be nonnegative")
        if self.numerator_unit != Unit.KILOGRAM_CO2E.value:
            raise ValueError("emissions factor numerator unit must be kgCO2e")
        if self.denominator_unit != Unit.KILOWATT_HOUR.value:
            raise ValueError("emissions factor denominator unit must be kWh")
        if isinstance(self.data_year, bool) or self.data_year <= 0:
            raise ValueError("emissions factor data year must be positive")
        metadata = {
            "geography": self.geography,
            "version": self.version,
            "intended purpose": self.intended_purpose,
            "source": self.source,
            "classification": self.classification,
        }
        if any(not value or value != value.strip() for value in metadata.values()):
            raise ValueError("emissions factor metadata must be nonempty and trimmed")
        if not self.included_gases or any(
            not gas or gas != gas.strip() for gas in self.included_gases
        ):
            raise ValueError("emissions factor included gases must be nonempty and trimmed")


@dataclass(frozen=True, slots=True)
class PurchasedElectricityEmissions:
    estimate: Emissions
    gross_import: Energy
    gross_export: Energy
    factor: EmissionsFactor
    name: str = "Purchased_Electricity_Emissions_Estimate"
    exclusions: tuple[str, ...] = ("on-site fuel emissions",)


@dataclass(frozen=True, slots=True)
class CleanEnergyAttribution:
    interval_id: Identifier
    direct_qualifying_generation_to_load: Energy
    qualifying_battery_discharge_to_load: Energy


@dataclass(frozen=True, slots=True)
class CleanEnergyShare:
    qualifying_energy: Energy
    served_load: Energy
    share: FiniteNumber | None


def calculate_purchased_electricity_emissions(
    intervals: Sequence[IntervalResult], factor: EmissionsFactor
) -> PurchasedElectricityEmissions:
    """Apply the declared factor to gross imports; exports and discharge never offset it."""

    gross_import = sum((item.grid_import.value for item in intervals), Decimal(0))
    gross_export = sum((item.grid_export.value for item in intervals), Decimal(0))
    return PurchasedElectricityEmissions(
        estimate=Emissions(gross_import * factor.value.value, Unit.KILOGRAM_CO2E),
        gross_import=Energy(gross_import, Unit.KILOWATT_HOUR),
        gross_export=Energy(gross_export, Unit.KILOWATT_HOUR),
        factor=factor,
    )


def calculate_clean_energy_share(
    schedule: Schedule,
    attributions: Sequence[CleanEnergyAttribution],
) -> CleanEnergyShare:
    """Calculate served-load share from explicitly tracked qualifying energy origins."""

    by_interval = {value.interval_id: value for value in attributions}
    expected_ids = {value.interval_id for value in schedule.intervals}
    if len(by_interval) != len(attributions) or set(by_interval) != expected_ids:
        raise ValueError("clean-energy attribution must cover every schedule interval exactly once")

    served_load = Decimal(0)
    qualifying_energy = Decimal(0)
    for interval in schedule.intervals:
        attribution = by_interval[interval.interval_id]
        served = interval.served_critical_load.value + interval.served_noncritical_load.value
        direct = attribution.direct_qualifying_generation_to_load.value
        stored = attribution.qualifying_battery_discharge_to_load.value
        if direct > interval.generation_dispatched.value:
            raise ValueError("direct qualifying energy exceeds dispatched generation")
        if stored > interval.battery_discharge.value:
            raise ValueError("qualifying stored energy exceeds battery discharge")
        if direct + stored > served:
            raise ValueError("qualifying energy exceeds served load")
        served_load += served
        qualifying_energy += direct + stored

    return CleanEnergyShare(
        qualifying_energy=Energy(qualifying_energy, Unit.KILOWATT_HOUR),
        served_load=Energy(served_load, Unit.KILOWATT_HOUR),
        share=None if served_load == 0 else FiniteNumber(qualifying_energy / served_load),
    )
