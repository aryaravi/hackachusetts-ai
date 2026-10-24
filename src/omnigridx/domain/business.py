"""Immutable public-business contracts shared by services and presentation."""

from dataclasses import dataclass, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from typing import Any

from .records import AlternativeType, ManifestDecimal, Sha256Digest, SourceRecord, VersionReference
from .values import (
    Diagnostic,
    DiagnosticCode,
    DomainValidationError,
    Duration,
    Energy,
    FiniteNumber,
    Identifier,
    Power,
    Timestamp,
)


def _invalid(field: str, message: str, code: DiagnosticCode = DiagnosticCode.OUT_OF_RANGE) -> None:
    raise DomainValidationError(Diagnostic(code, field, message))


def _required_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _invalid(field, "is required", DiagnosticCode.INVALID_IDENTIFIER)


def _required_tuple(value: tuple[Any, ...], field: str) -> None:
    if not value:
        _invalid(field, "must not be empty")


def _decimal_string(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f") if normalized else "0"


def _canonical(value: Any) -> Any:
    if isinstance(value, Timestamp):
        return value.instant_utc.isoformat().replace("+00:00", "Z")
    if isinstance(value, Identifier):
        return value.value
    if isinstance(value, Sha256Digest):
        return value.value
    if isinstance(value, VersionReference):
        return {"name": value.name, "version": value.version}
    if isinstance(value, (Energy, Power, Duration)):
        return {"unit": value.unit.value, "value": _decimal_string(value.value)}
    if isinstance(value, FiniteNumber):
        return _decimal_string(value.value)
    if isinstance(value, Decimal):
        return _decimal_string(value)
    if isinstance(value, (date, StrEnum)):
        return value.isoformat() if isinstance(value, date) else value.value
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    return value


class SectionStatus(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"


class RefreshOutcome(StrEnum):
    PUBLISHED = "published"
    UNCHANGED = "unchanged"
    FAILED = "failed"


class PolicyReviewStatus(StrEnum):
    REVIEWED = "reviewed"
    UNREVIEWED = "unreviewed"


class PolicyUse(StrEnum):
    INFORMATIONAL = "informational"
    CALCULATION = "calculation"


class ApplicabilityStatus(StrEnum):
    APPLICABLE = "applicable"
    INAPPLICABLE = "inapplicable"
    UNKNOWN = "unknown"
    NOT_EVALUATED = "not-evaluated"


class SeriesKind(StrEnum):
    HISTORICAL_DEMAND = "historical_demand"
    OFFICIAL_FORECAST = "official_published_demand_forecast"
    VALIDATED_BASELINE = "validated_baseline_forecast"
    LONG_RANGE_PROJECTION = "long_range_scenario_projection"
    SUPPLY_CONTEXT = "supply_context"


@dataclass(frozen=True, slots=True)
class AdapterDefinition:
    identifier: Identifier
    canonical_scheme: str
    canonical_host: str
    canonical_path: str
    media_types: tuple[str, ...]
    max_response_bytes: int
    connect_timeout: Duration
    read_timeout: Duration
    retry_limit: int
    dataset_schema: VersionReference
    freshness_threshold: Duration
    refresh_schedule: str

    def __post_init__(self) -> None:
        if self.canonical_scheme != "https":
            _invalid("canonical_scheme", "must be https")
        _required_text(self.canonical_host, "canonical_host")
        if "://" in self.canonical_host or "/" in self.canonical_host:
            _invalid("canonical_host", "must be a host without scheme or path")
        if not self.canonical_path.startswith("/"):
            _invalid("canonical_path", "must start with /")
        _required_tuple(self.media_types, "media_types")
        if self.max_response_bytes <= 0:
            _invalid("max_response_bytes", "must be positive")
        if self.connect_timeout.value <= 0 or self.read_timeout.value <= 0:
            _invalid("timeouts", "must be positive")
        if self.retry_limit < 0:
            _invalid("retry_limit", "must be nonnegative")
        _required_text(self.dataset_schema.name, "dataset_schema.name")
        _required_text(self.dataset_schema.version, "dataset_schema.version")
        if self.freshness_threshold.value <= 0:
            _invalid("freshness_threshold", "must be positive")
        _required_text(self.refresh_schedule, "refresh_schedule")


@dataclass(frozen=True, slots=True)
class RefreshRun:
    identifier: Identifier
    adapter_id: Identifier
    scheduled_at: Timestamp
    started_at: Timestamp
    completed_at: Timestamp
    outcome: RefreshOutcome
    content_hash: Sha256Digest | None
    validation_result: str
    candidate_dataset_version: VersionReference | None
    published_dataset_version: VersionReference | None
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if self.completed_at.instant_utc < self.started_at.instant_utc:
            _invalid("completed_at", "must not precede started_at")
        _required_text(self.validation_result, "validation_result")
        if self.outcome is RefreshOutcome.PUBLISHED and (
            self.content_hash is None or self.published_dataset_version is None
        ):
            _invalid("outcome", "published refresh requires content hash and Dataset version")


@dataclass(frozen=True, slots=True)
class DatasetDisplayMetadata:
    dataset_id: Identifier
    source_record_id: Identifier
    publisher: str
    canonical_url: str
    version_or_as_of: str
    retrieved_at: Timestamp
    geography: str
    units: tuple[str, ...]
    interval_or_cadence: str
    freshness_status: SectionStatus
    freshness_threshold: Duration

    def __post_init__(self) -> None:
        for field, value in (
            ("publisher", self.publisher),
            ("canonical_url", self.canonical_url),
            ("version_or_as_of", self.version_or_as_of),
            ("geography", self.geography),
            ("interval_or_cadence", self.interval_or_cadence),
        ):
            _required_text(value, field)
        if not self.canonical_url.startswith("https://"):
            _invalid("canonical_url", "must be HTTPS")
        _required_tuple(self.units, "units")
        if any(not unit.strip() for unit in self.units):
            _invalid("units", "must contain explicit units")
        if self.freshness_threshold.value <= 0:
            _invalid("freshness_threshold", "must be positive")


@dataclass(frozen=True, slots=True)
class PolicyRecord:
    identifier: Identifier
    issuer: str
    title: str
    canonical_url: str
    publication_date: date
    effective_period: str
    retrieved_at: Timestamp
    last_reviewed_at: Timestamp
    jurisdiction: str
    customer_applicability: str
    asset_applicability: str
    supersession_status: str
    successor_url: str | None
    reviewer: str
    review_status: PolicyReviewStatus
    use: PolicyUse

    def __post_init__(self) -> None:
        for field, value in (
            ("issuer", self.issuer),
            ("title", self.title),
            ("canonical_url", self.canonical_url),
            ("effective_period", self.effective_period),
            ("jurisdiction", self.jurisdiction),
            ("customer_applicability", self.customer_applicability),
            ("asset_applicability", self.asset_applicability),
            ("supersession_status", self.supersession_status),
            ("reviewer", self.reviewer),
        ):
            _required_text(value, field)
        if not self.canonical_url.startswith("https://"):
            _invalid("canonical_url", "must be HTTPS")
        if self.successor_url is not None and not self.successor_url.startswith("https://"):
            _invalid("successor_url", "must be HTTPS")


@dataclass(frozen=True, slots=True)
class PolicySnapshot:
    identity: VersionReference
    snapshot_date: date
    record_ids: tuple[Identifier, ...]
    content_hash: Sha256Digest

    def __post_init__(self) -> None:
        _required_text(self.identity.name, "identity.name")
        _required_text(self.identity.version, "identity.version")
        _required_tuple(self.record_ids, "record_ids")
        if len(set(self.record_ids)) != len(self.record_ids):
            _invalid("record_ids", "must be unique")


@dataclass(frozen=True, slots=True)
class AggregateScope:
    geography: str
    interval: Duration
    period_start: Timestamp
    period_end: Timestamp
    measurement_basis: str

    def __post_init__(self) -> None:
        _required_text(self.geography, "geography")
        _required_text(self.measurement_basis, "measurement_basis")
        if self.interval.value <= 0:
            _invalid("interval", "must be positive")
        if self.period_end.instant_utc <= self.period_start.instant_utc:
            _invalid("period_end", "must follow period_start")


@dataclass(frozen=True, slots=True)
class AggregatePoint:
    timestamp: Timestamp
    value: FiniteNumber
    unit: str
    available_at: Timestamp

    def __post_init__(self) -> None:
        _required_text(self.unit, "unit")


@dataclass(frozen=True, slots=True)
class AggregateSeries:
    kind: SeriesKind
    scope: AggregateScope
    dataset_version: VersionReference
    points: tuple[AggregatePoint, ...]
    metadata: DatasetDisplayMetadata
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        _required_tuple(self.points, "points")
        if any(point.unit not in self.metadata.units for point in self.points):
            _invalid("points.unit", "must be declared in Dataset metadata")


@dataclass(frozen=True, slots=True)
class OfficialPublishedForecast:
    identifier: Identifier
    scope: AggregateScope
    issue_time: Timestamp
    maximum_horizon: Duration
    target_variable: str
    methodology_reference: str
    published_error_or_coverage: str | None
    points: tuple[AggregatePoint, ...]
    dataset_version: VersionReference
    metadata: DatasetDisplayMetadata

    def __post_init__(self) -> None:
        if self.maximum_horizon.value <= 0:
            _invalid("maximum_horizon", "must be positive")
        _required_text(self.target_variable, "target_variable")
        _required_text(self.methodology_reference, "methodology_reference")
        _required_tuple(self.points, "points")


@dataclass(frozen=True, slots=True)
class ForecastError:
    horizon_intervals: int
    mean_absolute_error: FiniteNumber
    unit: str
    observation_count: int

    def __post_init__(self) -> None:
        if self.horizon_intervals <= 0 or self.observation_count <= 0:
            _invalid("forecast_error", "horizon and observation count must be positive")
        _required_text(self.unit, "unit")


@dataclass(frozen=True, slots=True)
class ForecastEvaluation:
    method: str
    issue_time: Timestamp
    maximum_validated_horizon: Duration
    training_period: str
    holdout_period: str
    comparator: str
    errors_by_horizon: tuple[ForecastError, ...]
    prediction_intervals: str
    input_dataset_versions: tuple[VersionReference, ...]

    def __post_init__(self) -> None:
        for field, value in (
            ("method", self.method),
            ("training_period", self.training_period),
            ("holdout_period", self.holdout_period),
            ("comparator", self.comparator),
            ("prediction_intervals", self.prediction_intervals),
        ):
            _required_text(value, field)
        if self.maximum_validated_horizon.value <= 0:
            _invalid("maximum_validated_horizon", "must be positive")
        _required_tuple(self.errors_by_horizon, "errors_by_horizon")
        _required_tuple(self.input_dataset_versions, "input_dataset_versions")


@dataclass(frozen=True, slots=True)
class StorageConfiguration:
    usable_capacity: Energy
    charge_limit: Power
    discharge_limit: Power
    reserve: Energy
    reserve_treatment: str
    initial_state_of_charge: Energy
    terminal_state_of_charge: Energy

    def __post_init__(self) -> None:
        _required_text(self.reserve_treatment, "reserve_treatment")
        if self.initial_state_of_charge.value > self.usable_capacity.value:
            _invalid("initial_state_of_charge", "must not exceed usable capacity")
        if self.terminal_state_of_charge.value > self.usable_capacity.value:
            _invalid("terminal_state_of_charge", "must not exceed usable capacity")


@dataclass(frozen=True, slots=True)
class ConstraintState:
    name: str
    bound: FiniteNumber
    unit: str
    interval_id: Identifier
    active: bool
    violated: bool

    def __post_init__(self) -> None:
        _required_text(self.name, "name")
        _required_text(self.unit, "unit")
        if self.active and self.violated:
            _invalid("constraint_state", "cannot be both active and violated")


@dataclass(frozen=True, slots=True)
class StorageAlternative:
    alternative: AlternativeType
    charge_energy: Energy | None
    discharge_energy: Energy | None
    conversion_losses: Energy | None
    peak_import: Power | None
    peak_interval_id: Identifier | None
    checker_passed: bool
    checker_diagnostics: tuple[str, ...]

    def __post_init__(self) -> None:
        metrics = (
            self.charge_energy,
            self.discharge_energy,
            self.conversion_losses,
            self.peak_import,
            self.peak_interval_id,
        )
        if self.checker_passed != all(value is not None for value in metrics):
            _invalid("checker_passed", "metrics are present if and only if checking passed")


@dataclass(frozen=True, slots=True)
class BusinessStorageView:
    scenario_version: VersionReference
    storage_configuration: StorageConfiguration
    alternatives: tuple[StorageAlternative, ...]
    peak_differences: tuple[ManifestDecimal, ...]
    constraints: tuple[ConstraintState, ...]
    labels: tuple[str, ...]
    assumptions: tuple[str, ...]
    exclusions: tuple[str, ...]

    def __post_init__(self) -> None:
        if tuple(item.alternative for item in self.alternatives) != tuple(AlternativeType):
            _invalid("alternatives", "must contain exactly existing, rule_based, and optimized")


@dataclass(frozen=True, slots=True)
class MaintenanceRequest:
    identifier: Identifier
    asset_id: Identifier
    horizon: AggregateScope
    allowed_start_intervals: tuple[Identifier, ...]
    duration_intervals: int
    asset_availability: tuple[Identifier, ...]
    operating_constraints: tuple[ManifestDecimal, ...]
    demand_forecast_version: VersionReference
    supply_context_version: VersionReference
    objective_components: tuple[ManifestDecimal, ...]
    checker_tolerance: Energy

    def __post_init__(self) -> None:
        _required_tuple(self.allowed_start_intervals, "allowed_start_intervals")
        _required_tuple(self.asset_availability, "asset_availability")
        _required_tuple(self.operating_constraints, "operating_constraints")
        _required_tuple(self.objective_components, "objective_components")
        if self.duration_intervals <= 0:
            _invalid("duration_intervals", "must be positive")
        if self.checker_tolerance.value < 0:
            _invalid("checker_tolerance", "must be nonnegative")


@dataclass(frozen=True, slots=True)
class MaintenancePlanResult:
    status: SectionStatus
    selected_start: Timestamp | None
    selected_end: Timestamp | None
    duration: Duration
    asset_id: Identifier
    objective_value: FiniteNumber | None
    objective_components: tuple[ManifestDecimal, ...]
    peak_impact: Power | None
    unserved_load_impact: Energy | None
    binding_constraints: tuple[str, ...]
    input_versions: tuple[VersionReference, ...]
    solver_status: str
    checker_status: str
    diagnostics: tuple[str, ...]

    def __post_init__(self) -> None:
        if (self.selected_start is None) != (self.selected_end is None):
            _invalid("selected_window", "start and end must both be present or absent")
        if self.selected_start and self.selected_end:
            if self.selected_end.instant_utc <= self.selected_start.instant_utc:
                _invalid("selected_end", "must follow selected_start")
            if self.objective_value is None:
                _invalid("objective_value", "is required for a selected plan")
        _required_text(self.solver_status, "solver_status")
        _required_text(self.checker_status, "checker_status")
        _required_tuple(self.input_versions, "input_versions")


@dataclass(frozen=True, slots=True)
class BusinessError:
    code: str
    dataset_id: Identifier | None
    field: str | None
    message: str

    def __post_init__(self) -> None:
        _required_text(self.code, "code")
        _required_text(self.message, "message")


@dataclass(frozen=True, slots=True)
class BusinessSection:
    identifier: Identifier
    status: SectionStatus
    data: dict[str, Any]
    errors: tuple[BusinessError, ...] = ()


@dataclass(frozen=True, slots=True)
class BusinessResponse:
    schema_version: str
    generated_at: Timestamp
    mode: str
    page: str
    status: SectionStatus
    sections: tuple[BusinessSection, ...]
    sources: tuple[DatasetDisplayMetadata, ...]
    limitations: tuple[str, ...]
    errors: tuple[BusinessError, ...]

    def __post_init__(self) -> None:
        _required_text(self.schema_version, "schema_version")
        if self.mode != "public-business":
            _invalid("mode", "must be public-business")
        _required_text(self.page, "page")
        if len({section.identifier for section in self.sections}) != len(self.sections):
            _invalid("sections", "identifiers must be unique")
        _required_tuple(self.limitations, "limitations")

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "page": self.page,
            "status": self.status.value,
            "sections": _canonical(self.sections),
            "sources": _canonical(self.sources),
            "limitations": list(self.limitations),
            "errors": _canonical(self.errors),
        }

    @property
    def fingerprint(self) -> Sha256Digest:
        payload = json.dumps(self.canonical_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return Sha256Digest(hashlib.sha256(payload.encode("utf-8")).hexdigest())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.canonical_dict(),
            "generated_at": _canonical(self.generated_at),
            "fingerprint": str(self.fingerprint),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


@dataclass(frozen=True, slots=True)
class PublicBusinessFixture:
    name: str
    filename: str
    media_type: str
    source: SourceRecord
    content_hash: Sha256Digest
    byte_length: int

    def __post_init__(self) -> None:
        _required_text(self.name, "name")
        _required_text(self.filename, "filename")
        _required_text(self.media_type, "media_type")
        if self.byte_length <= 0:
            _invalid("byte_length", "must be positive")


@dataclass(frozen=True, slots=True)
class PublicBusinessFixtureBundle:
    version: str
    fixtures: tuple[PublicBusinessFixture, ...]

    def __post_init__(self) -> None:
        _required_text(self.version, "version")
        if {item.name for item in self.fixtures} != {
            "historical_demand",
            "official_forecast",
            "policy",
            "supply_context",
        }:
            _invalid("fixtures", "must contain the four configured official-source schemas")
