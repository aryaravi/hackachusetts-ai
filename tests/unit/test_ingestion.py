from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from time import perf_counter

from omnigridx.application import (
    FreshnessPolicy,
    FreshnessStatus,
    IngestionConfig,
    IngestionDiagnosticCode,
    IngestionRepositories,
    LocalSnapshotIngestionService,
    decide_freshness,
)
from omnigridx.domain import (
    DatasetStatus,
    DatasetVersion,
    Duration,
    FiniteNumber,
    Identifier,
    NormalizedRecord,
    ProvenanceEdge,
    RawSnapshot,
    SourceRecord,
    Timestamp,
    Unit,
)
from omnigridx.infrastructure import (
    LocalCsvSourceAdapter,
    LocalSnapshotRepository,
    SQLiteAppendOnlyRepository,
)


def _source() -> SourceRecord:
    return SourceRecord(
        identifier=Identifier("source-1"),
        publisher="Authoritative Publisher",
        canonical_url="https://publisher.example/intervals.csv",
        discovery_url=None,
        dataset_identifier=Identifier("publisher-dataset-1"),
        retrieved_at=Timestamp(datetime(2024, 11, 4, tzinfo=UTC)),
        version_or_as_of="2024-11-03",
        geography="Massachusetts",
        units=("kWh",),
        cadence="1 hour",
        coverage="configured interval range",
        access_terms="Open data terms",
        quality_status="approved_snapshot",
        allowed_uses=("screening",),
        prohibited_uses=("site_load_proof",),
    )


def _config(start: datetime, end: datetime) -> IngestionConfig:
    return IngestionConfig(
        schema_version="1",
        canonical_unit=Unit.KILOWATT_HOUR,
        expected_geography="Massachusetts",
        cadence=Duration(1, Unit.HOUR),
        cadence_label="1 hour",
        coverage_start=Timestamp(start),
        coverage_end=Timestamp(end),
        plausible_minimum=FiniteNumber(0),
        plausible_maximum=FiniteNumber(100),
    )


def _service(tmp_path: Path) -> tuple[
    LocalSnapshotIngestionService,
    IngestionRepositories,
    LocalSnapshotRepository,
]:
    database = tmp_path / "metadata.sqlite3"
    snapshots = LocalSnapshotRepository(tmp_path / "objects")
    repositories = IngestionRepositories(
        sources=SQLiteAppendOnlyRepository(database, SourceRecord),
        snapshots=SQLiteAppendOnlyRepository(database, RawSnapshot),
        datasets=SQLiteAppendOnlyRepository(database, DatasetVersion),
        records=SQLiteAppendOnlyRepository(database, NormalizedRecord),
        provenance=SQLiteAppendOnlyRepository(database, ProvenanceEdge),
    )
    return (
        LocalSnapshotIngestionService(snapshots, repositories, LocalCsvSourceAdapter()),
        repositories,
        snapshots,
    )


def test_ingest_normalizes_dst_fold_and_persists_complete_provenance(tmp_path: Path) -> None:
    service, repositories, snapshots = _service(tmp_path)
    content = (
        b"record_key,timestamp,value,unit,geography\n"
        b"first,2024-11-03T01:30:00-04:00,10.5,kWh,Massachusetts\n"
        b"second,2024-11-03T01:30:00-05:00,11.5,kWh,Massachusetts\n"
    )

    result = service.ingest(
        Identifier("dataset-fold"),
        _source(),
        content,
        "text/csv",
        _config(
            datetime.fromisoformat("2024-11-03T01:30:00-04:00"),
            datetime.fromisoformat("2024-11-03T01:30:00-05:00"),
        ),
    )

    assert result.dataset.status is DatasetStatus.ACCEPTED
    assert result.dataset.download_duration is None
    assert result.dataset.processing_duration.value >= 0
    assert result.input_record_count == 2
    assert [record.timestamp.fold for record in result.records] == [0, 1]
    assert result.records[0].timestamp.local_datetime.replace(tzinfo=None) == result.records[
        1
    ].timestamp.local_datetime.replace(tzinfo=None)
    assert all(record.quality_flags == ("local_snapshot",) for record in result.records)
    assert len(result.provenance) == 2
    for record, edge in zip(result.records, result.provenance, strict=True):
        assert repositories.records.get(record.identifier) == record
        assert repositories.provenance.get(edge.identifier) == edge
        assert edge.source_locator == record.source_locator
    raw = repositories.snapshots.get(result.dataset.raw_snapshot_id)
    assert raw is not None
    assert snapshots.get_verified(raw) == content


def test_record_failures_are_partitioned_with_every_diagnostic(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)
    content = (
        "record_key,timestamp,value,unit,geography\n"
        "first,2026-01-01T00:00:00+00:00,10,kWh,Massachusetts\n"
        "second,2026-01-01T01:00:00+00:00,20,kWh,Massachusetts\n"
        "duplicate,2026-01-01T01:00:00+00:00,20,kWh,Massachusetts\n"
        "missing-unit,2026-01-01T02:00:00+00:00,20,,Massachusetts\n"
        "not-finite,2026-01-01T02:00:00+00:00,NaN,kWh,Massachusetts\n"
        "wrong-place,2026-01-01T02:00:00+00:00,20,kWh,Connecticut\n"
        "implausible,2026-01-01T02:00:00+00:00,101,kWh,Massachusetts\n"
    ).encode()

    result = service.ingest(
        Identifier("dataset-partition"),
        replace(_source(), retrieved_at=Timestamp(datetime(2026, 1, 2, tzinfo=UTC))),
        content,
        "text/csv",
        _config(
            datetime(2026, 1, 1, 0, tzinfo=UTC),
            datetime(2026, 1, 1, 1, tzinfo=UTC),
        ),
    )

    assert result.dataset.status is DatasetStatus.ACCEPTED
    assert (result.dataset.valid_record_count, result.dataset.rejected_record_count) == (2, 5)
    assert result.input_record_count == 7
    assert {item.code for item in result.diagnostics} == {
        IngestionDiagnosticCode.DUPLICATE_RECORD,
        IngestionDiagnosticCode.REQUIRED_FIELD_MISSING,
        IngestionDiagnosticCode.INVALID_VALUE,
        IngestionDiagnosticCode.GEOGRAPHY_MISMATCH,
        IngestionDiagnosticCode.VALUE_OUT_OF_RANGE,
    }
    assert {item.record for item in result.diagnostics} == {
        "row:4",
        "row:5",
        "row:6",
        "row:7",
        "row:8",
    }


def test_dataset_failures_publish_no_records_and_preserve_prior_version(tmp_path: Path) -> None:
    service, repositories, _ = _service(tmp_path)
    source = replace(_source(), retrieved_at=Timestamp(datetime(2026, 1, 2, tzinfo=UTC)))
    good = (
        b"record_key,timestamp,value,unit,geography\n"
        b"first,2026-01-01T00:00:00+00:00,10,kWh,Massachusetts\n"
        b"second,2026-01-01T01:00:00+00:00,20,kWh,Massachusetts\n"
    )
    first = service.ingest(
        Identifier("dataset-first"),
        source,
        good,
        "text/csv",
        _config(
            datetime(2026, 1, 1, 0, tzinfo=UTC),
            datetime(2026, 1, 1, 1, tzinfo=UTC),
        ),
    )
    bad = good.replace(b"01:00:00", b"02:00:00")
    second = service.ingest(
        Identifier("dataset-second"),
        source,
        bad,
        "text/csv",
        _config(
            datetime(2026, 1, 1, 0, tzinfo=UTC),
            datetime(2026, 1, 1, 1, tzinfo=UTC),
        ),
    )

    assert first.dataset.status is DatasetStatus.ACCEPTED
    assert second.dataset.status is DatasetStatus.REJECTED
    assert second.records == ()
    assert second.provenance == ()
    assert {item.code for item in second.diagnostics} == {
        IngestionDiagnosticCode.CADENCE_MISMATCH,
        IngestionDiagnosticCode.COVERAGE_MISMATCH,
    }
    assert repositories.datasets.get(first.dataset.identifier) == first.dataset
    assert repositories.datasets.get(second.dataset.identifier) == second.dataset


def test_incomplete_source_and_zero_valid_snapshot_are_rejected(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)
    incomplete = replace(
        _source(),
        identifier=Identifier("source-invalid"),
        publisher="",
        canonical_url="",
        version_or_as_of="",
        geography="",
        units=(),
        cadence="",
        coverage="",
        access_terms="",
        quality_status="",
        allowed_uses=(),
        prohibited_uses=(),
    )
    source_result = service.ingest(
        Identifier("dataset-source-invalid"),
        incomplete,
        b"not parsed because source metadata is incomplete",
        "text/csv",
        _config(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)),
    )
    zero_result = service.ingest(
        Identifier("dataset-zero-valid"),
        _source(),
        (
            b"record_key,timestamp,value,unit,geography\n"
            b"bad,not-a-time,not-a-number,kWh,Massachusetts\n"
        ),
        "text/csv",
        _config(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)),
    )

    assert source_result.dataset.status is DatasetStatus.REJECTED
    assert source_result.input_record_count == 0
    assert {
        item.field
        for item in source_result.diagnostics
        if item.code is IngestionDiagnosticCode.MISSING_SOURCE_METADATA
    } == {
        "publisher",
        "canonical_url",
        "version_or_as_of",
        "geography",
        "units",
        "cadence",
        "coverage",
        "access_terms",
        "quality_status",
        "allowed_uses",
        "prohibited_uses",
    }
    assert IngestionDiagnosticCode.SOURCE_UNIT_UNDECLARED in {
        item.code for item in source_result.diagnostics
    }
    assert zero_result.dataset.status is DatasetStatus.REJECTED
    assert {item.code for item in zero_result.diagnostics} == {
        IngestionDiagnosticCode.INVALID_TIMESTAMP,
        IngestionDiagnosticCode.INVALID_VALUE,
        IngestionDiagnosticCode.ZERO_VALID_RECORDS,
    }


def test_freshness_blocks_current_use_and_qualifies_historical_use(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)
    content = (
        b"record_key,timestamp,value,unit,geography\n"
        b"only,2026-01-01T00:00:00+00:00,10,kWh,Massachusetts\n"
    )
    dataset = service.ingest(
        Identifier("dataset-freshness"),
        replace(_source(), retrieved_at=Timestamp(datetime(2026, 1, 2, tzinfo=UTC))),
        content,
        "text/csv",
        _config(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)),
    ).dataset

    current = decide_freshness(
        dataset,
        FreshnessPolicy("current dispatch", timedelta(days=1), True),
        date(2026, 1, 2),
        "publisher snapshot",
    )
    blocked = decide_freshness(
        dataset,
        FreshnessPolicy("current dispatch", timedelta(days=1), True),
        date(2026, 1, 3),
        "publisher snapshot",
    )
    historical = decide_freshness(
        dataset,
        FreshnessPolicy("historical screening", timedelta(days=1), False),
        date(2026, 1, 3),
        "publisher snapshot",
    )

    assert current.status is FreshnessStatus.CURRENT and current.permitted
    assert blocked.status is FreshnessStatus.BLOCKED and not blocked.permitted
    assert historical.status is FreshnessStatus.QUALIFIED and historical.permitted
    assert blocked.qualification is not None
    assert historical.qualification is not None
    assert "2026-01-01" in blocked.qualification
    assert "publisher snapshot" in historical.qualification


def test_plausible_range_boundaries_are_accepted_and_durations_are_separate(
    tmp_path: Path,
) -> None:
    service, _, _ = _service(tmp_path)
    content = (
        b"record_key,timestamp,value,unit,geography\n"
        b"minimum,2026-01-01T00:00:00+00:00,0,kWh,Massachusetts\n"
        b"maximum,2026-01-01T01:00:00+00:00,100,kWh,Massachusetts\n"
    )

    result = service.ingest(
        Identifier("dataset-boundaries"),
        replace(_source(), retrieved_at=Timestamp(datetime(2026, 1, 2, tzinfo=UTC))),
        content,
        "text/csv",
        _config(
            datetime(2026, 1, 1, 0, tzinfo=UTC),
            datetime(2026, 1, 1, 1, tzinfo=UTC),
        ),
    )

    assert result.dataset.status is DatasetStatus.ACCEPTED
    assert [record.value.value for record in result.records] == [Decimal("0"), Decimal("100")]
    assert result.input_record_count == 2
    assert result.dataset.processing_duration.value >= 0
    assert result.dataset.download_duration is None


def test_local_csv_adapter_processes_one_million_generated_records() -> None:
    record_count = 1_000_000
    content = bytearray(b"record_key,timestamp,value,unit,geography\n")
    row_suffix = b",2026-01-01T00:00:00+00:00,1,kWh,Massachusetts\n"
    for index in range(record_count):
        content.extend(str(index).encode())
        content.extend(row_suffix)

    started = perf_counter()
    parsed_count = sum(
        1 for _ in LocalCsvSourceAdapter().parse(bytes(content), _source())
    )
    measured_processing_duration = perf_counter() - started

    assert parsed_count == record_count
    assert measured_processing_duration >= 0
