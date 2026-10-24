"""Validated value objects shared by OmniGridX domain models."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar
from zoneinfo import ZoneInfo

NumericInput = Decimal | int | float
_NEW_YORK = ZoneInfo("America/New_York")


class DiagnosticCode(StrEnum):
    """Stable machine-readable domain validation codes."""

    INVALID_IDENTIFIER = "INVALID_IDENTIFIER"
    INVALID_INTERVAL = "INVALID_INTERVAL"
    INVALID_NUMERIC_TYPE = "INVALID_NUMERIC_TYPE"
    INVALID_UNIT = "INVALID_UNIT"
    NON_FINITE_NUMBER = "NON_FINITE_NUMBER"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    TIMEZONE_REQUIRED = "TIMEZONE_REQUIRED"


class DiagnosticScope(StrEnum):
    RECORD = "record"
    DATASET = "dataset"
    DOMAIN = "domain"


class CapabilityStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    HACKATHON_DEMO = "Hackathon_Demo"
    FUTURE_CAPABILITY = "Future_Capability"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: DiagnosticCode
    field: str
    message: str
    scope: DiagnosticScope = DiagnosticScope.DOMAIN


class DomainValidationError(ValueError):
    """A domain validation failure independent of any transport or storage layer."""

    def __init__(self, diagnostic: Diagnostic) -> None:
        self.diagnostic = diagnostic
        super().__init__(f"{diagnostic.code}: {diagnostic.field}: {diagnostic.message}")


def _error(code: DiagnosticCode, field: str, message: str) -> DomainValidationError:
    return DomainValidationError(Diagnostic(code=code, field=field, message=message))


def _finite_decimal(value: NumericInput, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float)):
        raise _error(DiagnosticCode.INVALID_NUMERIC_TYPE, field, "must be numeric")
    number = Decimal(str(value)) if isinstance(value, float) else Decimal(value)
    if not number.is_finite():
        raise _error(DiagnosticCode.NON_FINITE_NUMBER, field, "must be finite")
    return number


@dataclass(frozen=True, slots=True, init=False)
class FiniteNumber:
    value: Decimal

    def __init__(self, value: NumericInput) -> None:
        object.__setattr__(self, "value", _finite_decimal(value, "value"))


class Unit(StrEnum):
    KILOWATT_HOUR = "kWh"
    KILOWATT = "kW"
    HOUR = "h"
    US_DOLLAR = "USD"
    KILOGRAM_CO2E = "kgCO2e"


@dataclass(frozen=True, slots=True, init=False)
class _Quantity:
    value: Decimal
    unit: Unit

    expected_unit: ClassVar[Unit]
    nonnegative: ClassVar[bool] = True

    def __init__(self, value: NumericInput, unit: Unit) -> None:
        if not isinstance(unit, Unit) or unit is not self.expected_unit:
            raise _error(
                DiagnosticCode.INVALID_UNIT,
                "unit",
                f"must be {self.expected_unit.value}",
            )
        number = _finite_decimal(value, "value")
        if self.nonnegative and number < 0:
            raise _error(DiagnosticCode.OUT_OF_RANGE, "value", "must be nonnegative")
        object.__setattr__(self, "value", number)
        object.__setattr__(self, "unit", unit)


class Energy(_Quantity):
    expected_unit = Unit.KILOWATT_HOUR


class Power(_Quantity):
    expected_unit = Unit.KILOWATT


class Duration(_Quantity):
    expected_unit = Unit.HOUR


class Money(_Quantity):
    expected_unit = Unit.US_DOLLAR
    nonnegative = False


class Emissions(_Quantity):
    expected_unit = Unit.KILOGRAM_CO2E


@dataclass(frozen=True, slots=True)
class Identifier:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value or self.value != self.value.strip():
            raise _error(
                DiagnosticCode.INVALID_IDENTIFIER,
                "identifier",
                "must be a nonempty string without surrounding whitespace",
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True, init=False)
class Timestamp:
    instant_utc: datetime
    local_datetime: datetime
    utc_offset: timedelta
    time_zone_name: str
    fold: int

    def __init__(self, value: datetime) -> None:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise _error(
                DiagnosticCode.TIMEZONE_REQUIRED,
                "timestamp",
                "must include an explicit UTC offset or named time zone",
            )
        instant_utc = value.astimezone(UTC)
        local_datetime = instant_utc.astimezone(_NEW_YORK)
        utc_offset = local_datetime.utcoffset()
        if utc_offset is None:  # pragma: no cover - ZoneInfo always supplies an offset
            raise _error(DiagnosticCode.TIMEZONE_REQUIRED, "timestamp", "has no UTC offset")
        object.__setattr__(self, "instant_utc", instant_utc)
        object.__setattr__(self, "local_datetime", local_datetime)
        object.__setattr__(self, "utc_offset", utc_offset)
        object.__setattr__(self, "time_zone_name", _NEW_YORK.key)
        object.__setattr__(self, "fold", local_datetime.fold)


@dataclass(frozen=True, slots=True)
class Interval:
    identifier: Identifier
    start: Timestamp
    duration: Duration

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, Identifier):
            raise _error(DiagnosticCode.INVALID_INTERVAL, "identifier", "must be an Identifier")
        if not isinstance(self.start, Timestamp):
            raise _error(DiagnosticCode.INVALID_INTERVAL, "start", "must be a Timestamp")
        if not isinstance(self.duration, Duration) or self.duration.value <= 0:
            raise _error(DiagnosticCode.INVALID_INTERVAL, "duration", "must be greater than zero")

    @property
    def end_utc(self) -> datetime:
        return self.start.instant_utc + timedelta(hours=float(self.duration.value))
