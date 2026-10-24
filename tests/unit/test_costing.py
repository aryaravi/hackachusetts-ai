from dataclasses import fields
from decimal import Decimal

import pytest

from omnigridx.application import (
    BUNDLED_SAMPLE_RATE_CONFIGURATION,
    SAMPLE_RATE_DISCLAIMER,
    SCREENING_ESTIMATE_LABEL,
    SampleCostCalculator,
    SampleScreeningRateConfiguration,
)
from omnigridx.domain import AlternativeType, Energy, FiniteNumber, Identifier, IntervalResult, Unit


def energy(value: str | int) -> Energy:
    return Energy(Decimal(value), Unit.KILOWATT_HOUR)


def interval(identifier: str, grid_import: str, grid_export: str) -> IntervalResult:
    zero = energy(0)
    return IntervalResult(
        run_id=Identifier("sample-run"),
        alternative_type=AlternativeType.EXISTING,
        interval_id=Identifier(identifier),
        generation_available=zero,
        generation_dispatched=zero,
        generation_curtailed=zero,
        grid_import=energy(grid_import),
        grid_export=energy(grid_export),
        battery_charge=zero,
        battery_discharge=zero,
        served_critical_load=zero,
        served_noncritical_load=zero,
        critical_unserved_load=zero,
        noncritical_unserved_load=zero,
        other_conversion_loss=zero,
        storage_conversion_loss=zero,
        state_of_charge_start=zero,
        state_of_charge_end=zero,
        constraint_check_passed=True,
    )


def test_sample_cost_matches_direct_decimal_oracle() -> None:
    config = BUNDLED_SAMPLE_RATE_CONFIGURATION
    result = SampleCostCalculator().calculate(
        (interval("i1", "4.5", "1"), interval("i2", "2.5", "2")),
        config,
    )

    assert result.gross_import.value == Decimal("7.0")
    assert result.gross_export.value == Decimal("3")
    assert result.import_charge.amount.value == Decimal("7.0") * Decimal("0.25")
    assert result.export_credit.amount.value == Decimal("3") * Decimal("0.08")
    assert result.operating_cost.amount.value == Decimal("1.51")


def test_bundled_configuration_and_all_cost_values_are_disclosed() -> None:
    config = BUNDLED_SAMPLE_RATE_CONFIGURATION
    result = SampleCostCalculator().calculate((), config)

    estimates = (
        value
        for item in fields(result)
        if item.name in {"import_charge", "export_credit", "operating_cost"}
        for value in (getattr(result, item.name),)
    )
    assert all(estimate.label == SCREENING_ESTIMATE_LABEL for estimate in estimates)
    assert config.version == "2026.1"
    assert config.currency is Unit.US_DOLLAR
    assert config.units == "USD/kWh"
    assert tuple(value.isoformat() for value in config.effective_period) == (
        "2026-01-01",
        "2026-12-31",
    )
    assert config.source_or_assumption_label
    assert config.exclusions
    assert result.disclaimer == SAMPLE_RATE_DISCLAIMER
    assert "not a verified tariff" in result.disclaimer
    assert "historical bill reconciliation" in result.disclaimer
    assert "account-applicability determination" in result.disclaimer
    assert "future-savings validation" in result.disclaimer


@pytest.mark.parametrize(
    ("import_rate", "export_credit"),
    (("-0.01", "0"), ("0", "-0.01")),
)
def test_rate_configuration_rejects_negative_rates(
    import_rate: str,
    export_credit: str,
) -> None:
    config = BUNDLED_SAMPLE_RATE_CONFIGURATION

    with pytest.raises(ValueError, match="nonnegative"):
        SampleScreeningRateConfiguration(
            identifier=config.identifier,
            version=config.version,
            effective_period=config.effective_period,
            import_rate_per_kwh=FiniteNumber(Decimal(import_rate)),
            export_credit_per_kwh=FiniteNumber(Decimal(export_credit)),
            currency=config.currency,
            source_or_assumption_label=config.source_or_assumption_label,
            exclusions=config.exclusions,
        )
