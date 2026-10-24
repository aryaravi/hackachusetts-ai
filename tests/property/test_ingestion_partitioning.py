from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings, strategies as st

from omnigridx.application import (
    IngestionConfig,
    IngestionDiagnosticCode,
    IngestionRepositories,
    LocalSnapshotIngestionService,
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

_ERROR_DETAILS = {
    "missing_unit": (
        IngestionDiagnosticCode.REQUIRED_FIELD_MISSING,
        "unit",
        "required_field",
    ),
    "invalid_timestamp": (
        IngestionDiagnosticCode.INVALID_TIMESTAMP,
        "timestamp",
        "explicit_timezone",
    ),
    "invalid_value": (
        IngestionDiagnosticCode.INVALID_VALUE,
        "value",
        "finite_numeric",
    ),
    "undeclared_unit": (
        IngestionDiagnosticCode.UNIT_UNDECLARED,
        "unit",
        "declared_unit",
    ),
    "wrong_geography": (
        IngestionDiagnosticCode.GEOGRAPHY_MISMATCH,
        "geography",
        "expected_geography",
    ),
    "out_of_range": (
        IngestionDiagnosticCode.VALUE_OUT_OF_RANGE,
        "value",
        "plausible_range",
    ),
    "duplicate": (
        IngestionDiagnosticCode.DUPLICATE_RECORD,
        "record_key,timestamp",
        "unique_record",
    ),
}


def _source() -> SourceRecord:
    return SourceRecord(
        identifier=Identifier("source-property-11"),
        publisher="Authoritative Publisher",
        canonical_url="https://publisher.example/intervals.csv",
        discovery_url=None,
        dataset_identifier=Identifier("publisher-property-11"),
        retrieved_at=Timestamp(datetime(2026, 1, 2, tzinfo=UTC)),
        version_or_as_of="2026-01-01",
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


def _service(root: Path) -> tuple[LocalSnapshotIngestionService, IngestionRepositories]:
    database = root / "metadata.sqlite3"
    repositories = IngestionRepositories(
        sources=SQLiteAppendOnlyRepository(database, SourceRecord),
        snapshots=SQLiteAppendOnlyRepository(database, RawSnapshot),
        datasets=SQLiteAppendOnlyRepository(database, DatasetVersion),
        records=SQLiteAppendOnlyRepository(database, NormalizedRecord),
        provenance=SQLiteAppendOnlyRepository(database, ProvenanceEdge),
    )
    service = LocalSnapshotIngestionService(
        LocalSnapshotRepository(root / "objects"),
        repositories,
        LocalCsvSourceAdapter(),
    )
    return service, repositories


def _invalid_row(kind: str, index: int, start: datetime) -> str:
    fields = [
        f"invalid-{index}",
        (start + timedelta(hours=index + 1)).isoformat(),
        "50",
        "kWh",
        "Massachusetts",
    ]
    if kind == "missing_unit":
        fields[3] = ""
    elif kind == "invalid_timestamp":
        fields[1] = "not-a-timestamp"
    elif kind == "invalid_value":
        fields[2] = "NaN"
    elif kind == "undeclared_unit":
        fields[3] = "kW"
    elif kind == "wrong_geography":
        fields[4] = "Connecticut"
    elif kind == "out_of_range":
        fields[2] = "101"
    elif kind == "duplicate":
        fields[1] = start.isoformat()
    return ",".join(fields)


# Feature: omnigridx, Property 11: Record validation partitions without corruption
# **Validates: Requirements 1.2, 1.4, 1.5, 1.6**
@given(
    valid_values=st.lists(
        st.decimals(
            min_value=Decimal("0"),
            max_value=Decimal("100"),
            places=3,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=1,
        max_size=6,
    ),
    invalid_kinds=st.lists(
        st.sampled_from(tuple(_ERROR_DETAILS)),
        min_size=1,
        max_size=7,
    ),
)
@settings(max_examples=100, deadline=None)
def test_record_validation_partitions_without_corrupting_prior_versions(
    valid_values: list[Decimal], invalid_kinds: list[str]
) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    valid_rows = [
        f"valid-{index},{(start + timedelta(hours=index)).isoformat()},{value},kWh,Massachusetts"
        for index, value in enumerate(valid_values)
    ]
    invalid_rows = [
        _invalid_row(kind, index, start)
        for index, kind in enumerate(invalid_kinds, start=len(valid_values))
    ]
    content = ("record_key,timestamp,value,unit,geography\n" + "\n".join(valid_rows + invalid_rows)).encode()

    with TemporaryDirectory() as temporary_directory:
        service, repositories = _service(Path(temporary_directory))
        accepted = service.ingest(
            Identifier("dataset-accepted"),
            _source(),
            content,
            "text/csv",
            _config(start, start + timedelta(hours=len(valid_values) - 1)),
        )

        assert accepted.dataset.status is DatasetStatus.ACCEPTED
        assert accepted.input_record_count == len(valid_values) + len(invalid_kinds)
        assert accepted.dataset.valid_record_count == len(valid_values)
        assert accepted.dataset.rejected_record_count == len(invalid_kinds)
        assert [record.record_key for record in accepted.records] == [
            f"valid-{index}" for index in range(len(valid_values))
        ]
        assert [record.value.value for record in accepted.records] == valid_values
        assert [record.source_locator for record in accepted.records] == [
            f"row:{index + 2}" for index in range(len(valid_values))
        ]

        expected_diagnostics = tuple(
            (
                _ERROR_DETAILS[kind][0],
                "record",
                _ERROR_DETAILS[kind][1],
                _ERROR_DETAILS[kind][2],
                f"row:{len(valid_values) + index + 2}",
            )
            for index, kind in enumerate(invalid_kinds)
        )
        assert tuple(
            (item.code, item.scope, item.field, item.rule, item.record)
            for item in accepted.diagnostics
        ) == expected_diagnostics

        prior_dataset = repositories.datasets.get(accepted.dataset.identifier)
        prior_records = tuple(
            repositories.records.get(record.identifier) for record in accepted.records
        )
        prior_provenance = tuple(
            repositories.provenance.get(edge.identifier) for edge in accepted.provenance
        )

        failed = service.ingest(
            Identifier("dataset-failed"),
            _source(),
            (
                "record_key,timestamp,value,unit,geography\n"
                f"candidate,{(start + timedelta(hours=1)).isoformat()},10,kWh,Massachusetts"
            ).encode(),
            "text/csv",
            _config(start, start),
        )

        assert failed.dataset.status is DatasetStatus.REJECTED
        assert failed.records == ()
        assert failed.provenance == ()
        assert tuple(item.code for item in failed.diagnostics) == (
            IngestionDiagnosticCode.COVERAGE_MISMATCH,
        )
        assert repositories.datasets.get(accepted.dataset.identifier) == prior_dataset
        assert tuple(
            repositories.records.get(record.identifier) for record in accepted.records
        ) == prior_records
        assert tuple(
            repositories.provenance.get(edge.identifier) for edge in accepted.provenance
        ) == prior_provenance
        assert repositories.datasets.get(failed.dataset.identifier) == failed.dataset
        assert repositories.records.get(Identifier("dataset-failed:record:2")) is None
        assert repositories.provenance.get(Identifier("dataset-failed:provenance:1")) is None
