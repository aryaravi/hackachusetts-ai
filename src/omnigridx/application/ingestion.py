"""Local-snapshot ingestion, validation, normalization, and freshness decisions."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from time import perf_counter
from typing import TypeVar

from omnigridx.application.ports import AppendOnlyRepository, SnapshotRepository, SourceAdapter
from omnigridx.domain.records import (
    DatasetStatus,
    DatasetVersion,
    NormalizedRecord,
    ProvenanceEdge,
    RawSnapshot,
    SourceRecord,
)
from omnigridx.domain.values import Duration, FiniteNumber, Identifier, Timestamp, Unit

_REQUIRED_SOURCE_TEXT = (
    "publisher",
    "canonical_url",
    "version_or_as_of",
    "geography",
    "cadence",
    "coverage",
    "access_terms",
    "quality_status",
)
_REQUIRED_RECORD_FIELDS = ("record_key", "timestamp", "value", "unit", "geography")
RecordT = TypeVar("RecordT")


class IngestionDiagnosticCode(StrEnum):
    MISSING_SOURCE_METADATA = "MISSING_SOURCE_METADATA"
    SOURCE_UNIT_UNDECLARED = "SOURCE_UNIT_UNDECLARED"
    SOURCE_CADENCE_MISMATCH = "SOURCE_CADENCE_MISMATCH"
    SOURCE_GEOGRAPHY_MISMATCH = "SOURCE_GEOGRAPHY_MISMATCH"
    PARSE_ERROR = "PARSE_ERROR"
    REQUIRED_FIELD_MISSING = "REQUIRED_FIELD_MISSING"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    INVALID_VALUE = "INVALID_VALUE"
    UNIT_UNDECLARED = "UNIT_UNDECLARED"
    GEOGRAPHY_MISMATCH = "GEOGRAPHY_MISMATCH"
    VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    CADENCE_MISMATCH = "CADENCE_MISMATCH"
    COVERAGE_MISMATCH = "COVERAGE_MISMATCH"
    ZERO_VALID_RECORDS = "ZERO_VALID_RECORDS"


@dataclass(frozen=True, slots=True)
class IngestionDiagnostic:
    identifier: Identifier
    code: IngestionDiagnosticCode
    scope: str
    field: str
    rule: str
    message: str
    record: str | None = None


@dataclass(frozen=True, slots=True)
class IngestionConfig:
    schema_version: str
    canonical_unit: Unit
    expected_geography: str
    cadence: Duration
    cadence_label: str
    coverage_start: Timestamp
    coverage_end: Timestamp
    plausible_minimum: FiniteNumber
    plausible_maximum: FiniteNumber

    def __post_init__(self) -> None:
        if not self.schema_version or not self.expected_geography or not self.cadence_label:
            raise ValueError("schema version, geography, and cadence label are required")
        if self.cadence.value <= 0:
            raise ValueError("cadence must be greater than zero")
        if self.coverage_end.instant_utc < self.coverage_start.instant_utc:
            raise ValueError("coverage end must not precede coverage start")
        if self.plausible_maximum.value < self.plausible_minimum.value:
            raise ValueError("plausible maximum must not be below minimum")


@dataclass(frozen=True, slots=True)
class IngestionRepositories:
    sources: AppendOnlyRepository[SourceRecord]
    snapshots: AppendOnlyRepository[RawSnapshot]
    datasets: AppendOnlyRepository[DatasetVersion]
    records: AppendOnlyRepository[NormalizedRecord]
    provenance: AppendOnlyRepository[ProvenanceEdge]


@dataclass(frozen=True, slots=True)
class IngestionResult:
    dataset: DatasetVersion
    input_record_count: int
    records: tuple[NormalizedRecord, ...]
    provenance: tuple[ProvenanceEdge, ...]
    diagnostics: tuple[IngestionDiagnostic, ...]


class FreshnessStatus(StrEnum):
    CURRENT = "current"
    BLOCKED = "blocked"
    QUALIFIED = "qualified"


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    use: str
    maximum_age: timedelta
    requires_current_data: bool

    def __post_init__(self) -> None:
        if not self.use or self.maximum_age < timedelta(0):
            raise ValueError("freshness use and a nonnegative maximum age are required")


@dataclass(frozen=True, slots=True)
class FreshnessDecision:
    status: FreshnessStatus
    permitted: bool
    dataset_as_of: date
    maximum_age: timedelta
    qualification: str | None


def decide_freshness(
    dataset: DatasetVersion,
    policy: FreshnessPolicy,
    on_date: date,
    source_condition: str,
) -> FreshnessDecision:
    age = on_date - dataset.as_of_date
    stale = age > policy.maximum_age
    if not stale:
        return FreshnessDecision(
            FreshnessStatus.CURRENT, True, dataset.as_of_date, policy.maximum_age, None
        )
    detail = (
        f"{policy.use}: dataset as of {dataset.as_of_date.isoformat()} exceeds "
        f"maximum age {policy.maximum_age}; source condition: {source_condition}"
    )
    if policy.requires_current_data:
        return FreshnessDecision(
            FreshnessStatus.BLOCKED, False, dataset.as_of_date, policy.maximum_age, detail
        )
    return FreshnessDecision(
        FreshnessStatus.QUALIFIED, True, dataset.as_of_date, policy.maximum_age, detail
    )


class LocalSnapshotIngestionService:
    """Ingest one immutable local snapshot through narrow repository ports."""

    def __init__(
        self,
        snapshot_repository: SnapshotRepository,
        repositories: IngestionRepositories,
        adapter: SourceAdapter[Mapping[str, str | None]],
    ) -> None:
        self._snapshot_repository = snapshot_repository
        self._repositories = repositories
        self._adapter = adapter

    def ingest(
        self,
        dataset_identifier: Identifier,
        source: SourceRecord,
        content: bytes,
        media_type: str,
        config: IngestionConfig,
    ) -> IngestionResult:
        started = perf_counter()
        snapshot = self._snapshot_repository.put_once(content, media_type)
        diagnostics: list[IngestionDiagnostic] = []
        candidates: list[NormalizedRecord] = []
        input_count = 0

        self._persist_unchanged(self._repositories.sources, source)
        self._persist_unchanged(self._repositories.snapshots, snapshot)
        self._validate_source(dataset_identifier, source, config, diagnostics)

        if not diagnostics:
            try:
                rows = self._adapter.parse(content, source)
                seen_keys: set[str] = set()
                seen_instants: set[datetime] = set()
                for input_count, row in enumerate(rows, start=1):
                    normalized = self._normalize_row(
                        dataset_identifier,
                        source,
                        config,
                        row,
                        input_count + 1,
                        seen_keys,
                        seen_instants,
                        diagnostics,
                    )
                    if normalized is not None:
                        candidates.append(normalized)
            except (UnicodeError, ValueError) as error:
                self._diagnostic(
                    dataset_identifier,
                    diagnostics,
                    IngestionDiagnosticCode.PARSE_ERROR,
                    "dataset",
                    "snapshot",
                    "parseable_csv",
                    str(error),
                )

            self._validate_dataset(dataset_identifier, config, candidates, diagnostics)

        status = (
            DatasetStatus.REJECTED
            if any(item.scope == "dataset" for item in diagnostics)
            else DatasetStatus.ACCEPTED
        )
        processing_hours = Decimal(str((perf_counter() - started) / 3600))
        as_of = (
            max(item.timestamp.instant_utc for item in candidates).date()
            if candidates
            else source.retrieved_at.instant_utc.date()
        )
        temporal_coverage = (
            f"{min(item.timestamp.instant_utc for item in candidates).isoformat()}/"
            f"{max(item.timestamp.instant_utc for item in candidates).isoformat()}"
            if candidates
            else "unavailable"
        )
        dataset = DatasetVersion(
            identifier=dataset_identifier,
            source_record_id=source.identifier,
            raw_snapshot_id=snapshot.identifier,
            schema_version=config.schema_version,
            status=status,
            valid_record_count=len(candidates),
            rejected_record_count=input_count - len(candidates),
            temporal_coverage=temporal_coverage,
            geographic_coverage=config.expected_geography,
            as_of_date=as_of,
            diagnostic_ids=tuple(item.identifier for item in diagnostics),
            processing_duration=Duration(processing_hours, Unit.HOUR),
            download_duration=None,
        )
        self._repositories.datasets.add(dataset)

        if status is DatasetStatus.REJECTED:
            return IngestionResult(dataset, input_count, (), (), tuple(diagnostics))

        edges = tuple(
            ProvenanceEdge(
                identifier=Identifier(f"{dataset_identifier}:provenance:{index}"),
                normalized_record_id=record.identifier,
                dataset_version_id=dataset_identifier,
                snapshot_hash=snapshot.sha256,
                source_record_id=source.identifier,
                source_locator=record.source_locator,
            )
            for index, record in enumerate(candidates, start=1)
        )
        for record in candidates:
            self._repositories.records.add(record)
        for edge in edges:
            self._repositories.provenance.add(edge)
        return IngestionResult(dataset, input_count, tuple(candidates), edges, tuple(diagnostics))

    @staticmethod
    def _persist_unchanged(
        repository: AppendOnlyRepository[RecordT], record: RecordT
    ) -> None:
        existing = repository.get(record.identifier)  # type: ignore[attr-defined]
        if existing is None:
            repository.add(record)
        elif existing != record:
            raise ValueError(f"immutable record {record.identifier} already has different content")  # type: ignore[attr-defined]

    def _validate_source(
        self,
        dataset_identifier: Identifier,
        source: SourceRecord,
        config: IngestionConfig,
        diagnostics: list[IngestionDiagnostic],
    ) -> None:
        for field in _REQUIRED_SOURCE_TEXT:
            value = getattr(source, field)
            if not isinstance(value, str) or not value.strip():
                self._diagnostic(
                    dataset_identifier,
                    diagnostics,
                    IngestionDiagnosticCode.MISSING_SOURCE_METADATA,
                    "dataset",
                    field,
                    "required_source_metadata",
                    f"source metadata {field} is required",
                )
        for field in ("units", "allowed_uses", "prohibited_uses"):
            if not getattr(source, field):
                self._diagnostic(
                    dataset_identifier,
                    diagnostics,
                    IngestionDiagnosticCode.MISSING_SOURCE_METADATA,
                    "dataset",
                    field,
                    "required_source_metadata",
                    f"source metadata {field} is required",
                )
        if config.canonical_unit.value not in source.units:
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.SOURCE_UNIT_UNDECLARED,
                "dataset",
                "units",
                "declared_unit",
                f"source does not declare {config.canonical_unit.value}",
            )
        if source.cadence != config.cadence_label:
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.SOURCE_CADENCE_MISMATCH,
                "dataset",
                "cadence",
                "declared_cadence",
                f"source cadence must be {config.cadence_label}",
            )
        if source.geography != config.expected_geography:
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.SOURCE_GEOGRAPHY_MISMATCH,
                "dataset",
                "geography",
                "declared_geography",
                f"source geography must be {config.expected_geography}",
            )

    def _normalize_row(
        self,
        dataset_identifier: Identifier,
        source: SourceRecord,
        config: IngestionConfig,
        row: Mapping[str, str | None],
        line_number: int,
        seen_keys: set[str],
        seen_instants: set[datetime],
        diagnostics: list[IngestionDiagnostic],
    ) -> NormalizedRecord | None:
        locator = f"row:{line_number}"
        missing = [field for field in _REQUIRED_RECORD_FIELDS if not (row.get(field) or "").strip()]
        for field in missing:
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.REQUIRED_FIELD_MISSING,
                "record",
                field,
                "required_field",
                f"{field} is required",
                locator,
            )
        if missing:
            return None

        record_key = str(row["record_key"])
        timestamp: Timestamp | None = None
        value: FiniteNumber | None = None
        unit: Unit | None = None
        try:
            timestamp = Timestamp(datetime.fromisoformat(str(row["timestamp"])))
        except (TypeError, ValueError):
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.INVALID_TIMESTAMP,
                "record",
                "timestamp",
                "explicit_timezone",
                "timestamp must be ISO-8601 with an explicit UTC offset or named time zone",
                locator,
            )
        try:
            value = FiniteNumber(Decimal(str(row["value"])))
        except (InvalidOperation, ValueError):
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.INVALID_VALUE,
                "record",
                "value",
                "finite_numeric",
                "value must be numeric and finite",
                locator,
            )
        try:
            unit = Unit(str(row["unit"]))
            if unit is not config.canonical_unit or unit.value not in source.units:
                raise ValueError
        except ValueError:
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.UNIT_UNDECLARED,
                "record",
                "unit",
                "declared_unit",
                f"unit must be declared as {config.canonical_unit.value}",
                locator,
            )
        if row["geography"] != config.expected_geography:
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.GEOGRAPHY_MISMATCH,
                "record",
                "geography",
                "expected_geography",
                f"geography must be {config.expected_geography}",
                locator,
            )
        if value is not None and not (
            config.plausible_minimum.value <= value.value <= config.plausible_maximum.value
        ):
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.VALUE_OUT_OF_RANGE,
                "record",
                "value",
                "plausible_range",
                "value is outside the configured plausible range",
                locator,
            )
        if timestamp is not None and (
            record_key in seen_keys or timestamp.instant_utc in seen_instants
        ):
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.DUPLICATE_RECORD,
                "record",
                "record_key,timestamp",
                "unique_record",
                "record key and timestamp must be unique",
                locator,
            )
        if any(item.record == locator for item in diagnostics):
            return None
        assert timestamp is not None and value is not None and unit is not None
        seen_keys.add(record_key)
        seen_instants.add(timestamp.instant_utc)
        return NormalizedRecord(
            identifier=Identifier(f"{dataset_identifier}:record:{line_number}"),
            dataset_version_id=dataset_identifier,
            record_key=record_key,
            source_locator=locator,
            timestamp=timestamp,
            value=value,
            canonical_unit=unit,
            quality_flags=("local_snapshot",),
        )

    def _validate_dataset(
        self,
        dataset_identifier: Identifier,
        config: IngestionConfig,
        candidates: list[NormalizedRecord],
        diagnostics: list[IngestionDiagnostic],
    ) -> None:
        if not candidates:
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.ZERO_VALID_RECORDS,
                "dataset",
                "records",
                "at_least_one_valid_record",
                "dataset contains no valid records",
            )
            return
        ordered = sorted(candidates, key=lambda item: item.timestamp.instant_utc)
        expected_delta = timedelta(hours=float(config.cadence.value))
        for previous, current in zip(ordered, ordered[1:]):
            if current.timestamp.instant_utc - previous.timestamp.instant_utc != expected_delta:
                self._diagnostic(
                    dataset_identifier,
                    diagnostics,
                    IngestionDiagnosticCode.CADENCE_MISMATCH,
                    "dataset",
                    "timestamp",
                    "fixed_cadence",
                    f"{current.source_locator} does not follow {config.cadence_label} cadence",
                )
        if (
            ordered[0].timestamp.instant_utc != config.coverage_start.instant_utc
            or ordered[-1].timestamp.instant_utc != config.coverage_end.instant_utc
        ):
            self._diagnostic(
                dataset_identifier,
                diagnostics,
                IngestionDiagnosticCode.COVERAGE_MISMATCH,
                "dataset",
                "timestamp",
                "required_coverage",
                "normalized records do not cover the configured start and end",
            )

    @staticmethod
    def _diagnostic(
        dataset_identifier: Identifier,
        diagnostics: list[IngestionDiagnostic],
        code: IngestionDiagnosticCode,
        scope: str,
        field: str,
        rule: str,
        message: str,
        record: str | None = None,
    ) -> None:
        diagnostics.append(
            IngestionDiagnostic(
                Identifier(f"{dataset_identifier}:diagnostic:{len(diagnostics) + 1}"),
                code,
                scope,
                field,
                rule,
                message,
                record,
            )
        )
