from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3

import pytest

from omnigridx.domain import (
    DatasetStatus,
    DatasetVersion,
    Duration,
    FiniteNumber,
    Identifier,
    NormalizedRecord,
    ProvenanceEdge,
    RawSnapshot,
    Sha256Digest,
    SourceRecord,
    Timestamp,
    Unit,
)
from omnigridx.infrastructure import (
    AppendOnlyViolation,
    LocalSnapshotRepository,
    SQLiteAppendOnlyRepository,
)


def source_record() -> SourceRecord:
    return SourceRecord(
        identifier=Identifier("source-1"),
        publisher="Authoritative Publisher",
        canonical_url="https://publisher.example/data",
        discovery_url="https://catalog.example/discovery",
        dataset_identifier=Identifier("publisher-dataset-1"),
        retrieved_at=Timestamp(datetime(2026, 2, 1, tzinfo=UTC)),
        version_or_as_of="2026-01-31",
        geography="Massachusetts",
        units=("kWh",),
        cadence="15 minutes",
        coverage="2026-01-01/2026-01-31",
        access_terms="Open data terms",
        quality_status="approved_snapshot",
        allowed_uses=("screening",),
        prohibited_uses=("site_load_proof",),
    )


def dataset(identifier: str, snapshot: RawSnapshot, status: DatasetStatus) -> DatasetVersion:
    return DatasetVersion(
        identifier=Identifier(identifier),
        source_record_id=Identifier("source-1"),
        raw_snapshot_id=snapshot.identifier,
        schema_version="1",
        status=status,
        valid_record_count=1 if status is DatasetStatus.ACCEPTED else 0,
        rejected_record_count=0 if status is DatasetStatus.ACCEPTED else 1,
        temporal_coverage="2026-01-01/2026-01-31",
        geographic_coverage="Massachusetts",
        as_of_date=date(2026, 1, 31),
        diagnostic_ids=(Identifier("diagnostic-1"),) if status is DatasetStatus.REJECTED else (),
        processing_duration=Duration(0.001, Unit.HOUR),
        download_duration=None,
    )


def test_sqlite_persists_complete_provenance_and_prior_versions(tmp_path: Path) -> None:
    database = tmp_path / "metadata.sqlite3"
    snapshots = LocalSnapshotRepository(tmp_path / "objects")
    snapshot = snapshots.put_once(b"timestamp,value\n2026-01-01T00:00:00Z,1", "text/csv")

    sources = SQLiteAppendOnlyRepository(database, SourceRecord)
    raw_snapshots = SQLiteAppendOnlyRepository(database, RawSnapshot)
    datasets = SQLiteAppendOnlyRepository(database, DatasetVersion)
    records = SQLiteAppendOnlyRepository(database, NormalizedRecord)
    edges = SQLiteAppendOnlyRepository(database, ProvenanceEdge)

    source = source_record()
    accepted = dataset("dataset-1", snapshot, DatasetStatus.ACCEPTED)
    normalized = NormalizedRecord(
        identifier=Identifier("record-1"),
        dataset_version_id=accepted.identifier,
        record_key="interval-1",
        source_locator="row:2",
        timestamp=Timestamp(datetime(2026, 1, 1, tzinfo=UTC)),
        value=FiniteNumber(1),
        canonical_unit=Unit.KILOWATT_HOUR,
        quality_flags=("source_snapshot",),
    )
    edge = ProvenanceEdge(
        identifier=Identifier("edge-1"),
        normalized_record_id=normalized.identifier,
        dataset_version_id=accepted.identifier,
        snapshot_hash=snapshot.sha256,
        source_record_id=source.identifier,
        source_locator="row:2",
    )

    sources.add(source)
    raw_snapshots.add(snapshot)
    datasets.add(accepted)
    records.add(normalized)
    with pytest.raises(AppendOnlyViolation, match="does not match immutable history"):
        edges.add(
            replace(
                edge,
                identifier=Identifier("edge-with-wrong-locator"),
                source_locator="row:99",
            )
        )
    edges.add(edge)
    rejected = dataset("dataset-2", snapshot, DatasetStatus.REJECTED)
    datasets.add(rejected)

    assert database.is_file()
    with sqlite3.connect(database) as connection:
        database_location = connection.execute("PRAGMA database_list").fetchone()[2]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
    assert Path(database_location) == database.resolve()
    assert journal_mode == "wal"
    assert sources.get(source.identifier) == source
    assert raw_snapshots.get(snapshot.identifier) == snapshot
    assert datasets.get(accepted.identifier) == accepted
    assert datasets.get(rejected.identifier) == rejected
    assert records.get(normalized.identifier) == normalized
    assert edges.get(edge.identifier) == edge
    assert snapshots.get_verified(snapshot).startswith(b"timestamp,value")


def test_sqlite_rejects_replacement_update_delete_and_missing_lineage(tmp_path: Path) -> None:
    database = tmp_path / "metadata.sqlite3"
    sources = SQLiteAppendOnlyRepository(database, SourceRecord)
    source = source_record()
    sources.add(source)

    with pytest.raises(AppendOnlyViolation):
        sources.add(replace(source, publisher="Replacement Publisher"))

    missing_snapshot = RawSnapshot(
        identifier=Identifier("missing-snapshot"),
        sha256=source_record_hash(),
        byte_length=0,
        media_type="text/csv",
        storage_uri="file:///missing",
        received_at=Timestamp(datetime(2026, 2, 1, tzinfo=UTC)),
    )
    datasets = SQLiteAppendOnlyRepository(database, DatasetVersion)
    with pytest.raises(AppendOnlyViolation, match="missing immutable history"):
        datasets.add(dataset("dataset-with-missing-snapshot", missing_snapshot, DatasetStatus.REJECTED))

    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE source_records SET payload = '{}' WHERE identifier = 'source-1'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM source_records WHERE identifier = 'source-1'")

    assert sources.get(source.identifier) == source


def source_record_hash() -> Sha256Digest:
    return Sha256Digest("a" * 64)
