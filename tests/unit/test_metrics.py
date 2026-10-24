from dataclasses import replace
from decimal import Decimal

import pytest

from omnigridx.application import (
    CleanEnergyAttribution,
    EmissionsFactor,
    calculate_clean_energy_share,
    calculate_purchased_electricity_emissions,
)
from omnigridx.domain import (
    AlternativeType,
    Energy,
    FiniteNumber,
    Identifier,
    IntervalResult,
    Schedule,
    Unit,
)


def energy(value: str | int) -> Energy:
    return Energy(Decimal(value), Unit.KILOWATT_HOUR)


def interval(
    identifier: str,
    *,
    generation: str | int,
    grid_import: str | int,
    grid_export: str | int,
    battery_charge: str | int,
    battery_discharge: str | int,
    served: str | int,
    soc_start: str | int,
    soc_end: str | int,
) -> IntervalResult:
    zero = energy(0)
    return IntervalResult(
        run_id=Identifier("run-1"),
        alternative_type=AlternativeType.EXISTING,
        interval_id=Identifier(identifier),
        generation_available=energy(generation),
        generation_dispatched=energy(generation),
        generation_curtailed=zero,
        grid_import=energy(grid_import),
        grid_export=energy(grid_export),
        battery_charge=energy(battery_charge),
        battery_discharge=energy(battery_discharge),
        served_critical_load=energy(served),
        served_noncritical_load=zero,
        critical_unserved_load=zero,
        noncritical_unserved_load=zero,
        other_conversion_loss=zero,
        storage_conversion_loss=zero,
        state_of_charge_start=energy(soc_start),
        state_of_charge_end=energy(soc_end),
        constraint_check_passed=True,
    )


def schedule() -> Schedule:
    return Schedule(
        Identifier("schedule-1"),
        Identifier("scenario-1"),
        AlternativeType.EXISTING,
        (
            interval(
                "charge",
                generation=3,
                grid_import=5,
                grid_export=2,
                battery_charge=3,
                battery_discharge=0,
                served=3,
                soc_start=0,
                soc_end=3,
            ),
            interval(
                "discharge",
                generation=1,
                grid_import=0,
                grid_export=0,
                battery_charge=0,
                battery_discharge=2,
                served=3,
                soc_start=3,
                soc_end=1,
            ),
        ),
    )


def factor() -> EmissionsFactor:
    return EmissionsFactor(
        value=FiniteNumber(Decimal("0.4")),
        numerator_unit="kgCO2e",
        denominator_unit="kWh",
        geography="ISO-NE",
        data_year=2022,
        version="egrid-2022-v1",
        included_gases=("CO2", "CH4", "N2O"),
        intended_purpose="inventory screening",
        source="EPA eGRID",
        classification="average",
    )


def test_emissions_use_gross_imports_and_report_exports_with_complete_factor_metadata() -> None:
    result = calculate_purchased_electricity_emissions(schedule().intervals, factor())

    assert result.estimate.value == Decimal("2.0")
    assert result.gross_import == energy(5)
    assert result.gross_export == energy(2)
    assert result.name == "Purchased_Electricity_Emissions_Estimate"
    assert result.exclusions == ("on-site fuel emissions",)
    assert result.factor == factor()
    assert result.factor.included_gases == ("CO2", "CH4", "N2O")
    assert result.factor.intended_purpose == "inventory screening"


def test_clean_energy_share_uses_only_explicit_direct_and_storage_origin_attribution() -> None:
    value = schedule()
    result = calculate_clean_energy_share(
        value,
        (
            CleanEnergyAttribution(Identifier("charge"), energy(1), energy(0)),
            CleanEnergyAttribution(Identifier("discharge"), energy(0), energy(1)),
        ),
    )

    assert result.qualifying_energy == energy(2)
    assert result.served_load == energy(6)
    assert result.share == FiniteNumber(Decimal(1) / Decimal(3))


def test_clean_energy_share_is_not_applicable_when_served_load_is_zero() -> None:
    empty = replace(
        schedule(),
        intervals=(
            interval(
                "zero",
                generation=0,
                grid_import=0,
                grid_export=0,
                battery_charge=0,
                battery_discharge=0,
                served=0,
                soc_start=0,
                soc_end=0,
            ),
        ),
    )

    result = calculate_clean_energy_share(
        empty,
        (CleanEnergyAttribution(Identifier("zero"), energy(0), energy(0)),),
    )

    assert result.share is None
    assert result.served_load == energy(0)


def test_clean_energy_share_rejects_untracked_or_impossible_origin_claims() -> None:
    value = schedule()
    with pytest.raises(ValueError, match="every schedule interval"):
        calculate_clean_energy_share(
            value,
            (CleanEnergyAttribution(Identifier("charge"), energy(1), energy(0)),),
        )
    with pytest.raises(ValueError, match="exceeds battery discharge"):
        calculate_clean_energy_share(
            value,
            (
                CleanEnergyAttribution(Identifier("charge"), energy(0), energy(1)),
                CleanEnergyAttribution(Identifier("discharge"), energy(0), energy(0)),
            ),
        )
