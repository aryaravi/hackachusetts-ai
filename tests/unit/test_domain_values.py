from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import inf, nan
from zoneinfo import ZoneInfo

import pytest

from omnigridx.domain import (
    CapabilityStatus,
    DiagnosticCode,
    DomainValidationError,
    Duration,
    Emissions,
    Energy,
    FiniteNumber,
    Identifier,
    Interval,
    Money,
    Power,
    Timestamp,
    Unit,
)


def assert_error(code: DiagnosticCode, action: object) -> None:
    assert callable(action)
    with pytest.raises(DomainValidationError) as raised:
        action()
    assert raised.value.diagnostic.code is code


def test_finite_number_accepts_numeric_inputs_without_float_artifacts() -> None:
    assert FiniteNumber(2).value == Decimal("2")
    assert FiniteNumber(0.1).value == Decimal("0.1")
    assert FiniteNumber(Decimal("-3.25")).value == Decimal("-3.25")


@pytest.mark.parametrize("value", [nan, inf, -inf, Decimal("NaN"), Decimal("Infinity")])
def test_finite_number_rejects_non_finite_values(value: float | Decimal) -> None:
    assert_error(DiagnosticCode.NON_FINITE_NUMBER, lambda: FiniteNumber(value))


@pytest.mark.parametrize("value", [True, "1", None])
def test_finite_number_rejects_non_numeric_values(value: object) -> None:
    assert_error(DiagnosticCode.INVALID_NUMERIC_TYPE, lambda: FiniteNumber(value))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("quantity_type", "unit"),
    [
        (Energy, Unit.KILOWATT_HOUR),
        (Power, Unit.KILOWATT),
        (Duration, Unit.HOUR),
        (Emissions, Unit.KILOGRAM_CO2E),
    ],
)
def test_physical_quantities_require_explicit_units_and_nonnegative_values(
    quantity_type: type[Energy] | type[Power] | type[Duration] | type[Emissions],
    unit: Unit,
) -> None:
    assert quantity_type(Decimal("1.5"), unit).value == Decimal("1.5")
    assert_error(DiagnosticCode.OUT_OF_RANGE, lambda: quantity_type(-1, unit))
    assert_error(DiagnosticCode.INVALID_UNIT, lambda: quantity_type(1, Unit.US_DOLLAR))


def test_money_allows_credits_but_requires_currency() -> None:
    assert Money(Decimal("-2.50"), Unit.US_DOLLAR).value == Decimal("-2.50")
    assert_error(DiagnosticCode.INVALID_UNIT, lambda: Money(1, Unit.KILOWATT_HOUR))


def test_identifier_rejects_empty_or_ambiguous_whitespace() -> None:
    assert str(Identifier("interval-1")) == "interval-1"
    for value in ("", " ", " interval-1", "interval-1 "):
        assert_error(DiagnosticCode.INVALID_IDENTIFIER, lambda value=value: Identifier(value))


def test_timestamp_preserves_distinct_new_york_dst_folds() -> None:
    new_york = ZoneInfo("America/New_York")
    first = Timestamp(datetime(2024, 11, 3, 1, 30, tzinfo=new_york, fold=0))
    second = Timestamp(datetime(2024, 11, 3, 1, 30, tzinfo=new_york, fold=1))

    assert first.instant_utc == datetime(2024, 11, 3, 5, 30, tzinfo=UTC)
    assert second.instant_utc == datetime(2024, 11, 3, 6, 30, tzinfo=UTC)
    assert (first.fold, second.fold) == (0, 1)
    assert (first.utc_offset, second.utc_offset) == (timedelta(hours=-4), timedelta(hours=-5))
    assert first.time_zone_name == second.time_zone_name == "America/New_York"


def test_timestamp_converts_explicit_offsets_and_rejects_naive_values() -> None:
    timestamp = Timestamp(datetime(2024, 1, 1, 12, tzinfo=UTC))
    assert timestamp.local_datetime == datetime(
        2024, 1, 1, 7, tzinfo=ZoneInfo("America/New_York")
    )
    assert_error(DiagnosticCode.TIMEZONE_REQUIRED, lambda: Timestamp(datetime(2024, 1, 1)))


def test_interval_requires_positive_duration_and_exposes_utc_end() -> None:
    start = Timestamp(datetime(2024, 1, 1, tzinfo=UTC))
    interval = Interval(Identifier("i-1"), start, Duration(Decimal("0.25"), Unit.HOUR))
    assert interval.end_utc == datetime(2024, 1, 1, 0, 15, tzinfo=UTC)
    assert_error(
        DiagnosticCode.INVALID_INTERVAL,
        lambda: Interval(Identifier("i-1"), start, Duration(0, Unit.HOUR)),
    )


def test_capability_status_values_are_stable_domain_labels() -> None:
    assert CapabilityStatus.UNSUPPORTED.value == "unsupported"
    assert CapabilityStatus.HACKATHON_DEMO.value == "Hackathon_Demo"
    assert CapabilityStatus.FUTURE_CAPABILITY.value == "Future_Capability"
