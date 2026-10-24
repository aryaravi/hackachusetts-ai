"""SQLite-backed append-only repositories for ingestion provenance records."""

from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from typing import Any, Generic, TypeVar, cast

from omnigridx.domain.records import (
    DatasetStatus,
    DatasetVersion,
    NormalizedRecord,
    ProvenanceEdge,
    RawSnapshot,
    Sha256Digest,
    SourceRecord,
)
from omnigridx.domain.values import Duration, FiniteNumber, Identifier, Timestamp, Unit

PersistedRecord = SourceRecord | RawSnapshot | DatasetVersion | NormalizedRecord | ProvenanceEdge
RecordT = TypeVar("RecordT", bound=PersistedRecord)
_RECORD_TABLES: dict[type[object], str] = {
    SourceRecord: "source_records",
    RawSnapshot: "raw_snapshots",
    DatasetVersion: "dataset_versions",
    NormalizedRecord: "normalized_records",
    ProvenanceEdge: "provenance_edges",
}
_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS source_records (
    identifier TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_snapshots (
    identifier TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dataset_versions (
    identifier TEXT PRIMARY KEY,
    source_record_id TEXT NOT NULL REFERENCES source_records(identifier),
    raw_snapshot_id TEXT NOT NULL REFERENCES raw_snapshots(identifier),
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS normalized_records (
    identifier TEXT PRIMARY KEY,
    dataset_version_id TEXT NOT NULL REFERENCES dataset_versions(identifier),
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS provenance_edges (
    identifier TEXT PRIMARY KEY,
    normalized_record_id TEXT NOT NULL REFERENCES normalized_records(identifier),
    dataset_version_id TEXT NOT NULL REFERENCES dataset_versions(identifier),
    snapshot_hash TEXT NOT NULL REFERENCES raw_snapshots(sha256),
    source_record_id TEXT NOT NULL REFERENCES source_records(identifier),
    payload TEXT NOT NULL
);
"""


class AppendOnlyViolation(ValueError):
    """A persistence operation attempted to replace or remove immutable history."""


class PersistenceIntegrityError(ValueError):
    """Stored record data is malformed or internally inconsistent."""


def _timestamp_payload(value: Timestamp) -> dict[str, str | int]:
    return {
        "instant_utc": value.instant_utc.isoformat(),
        "local_datetime": value.local_datetime.isoformat(),
        "utc_offset_seconds": int(value.utc_offset.total_seconds()),
        "time_zone_name": value.time_zone_name,
        "fold": value.fold,
    }


def _timestamp(value: object) -> Timestamp:
    if not isinstance(value, dict) or not isinstance(value.get("instant_utc"), str):
        raise PersistenceIntegrityError("stored timestamp is malformed")
    result = Timestamp(datetime.fromisoformat(value["instant_utc"]))
    if value != _timestamp_payload(result):
        raise PersistenceIntegrityError("stored timestamp representations disagree")
    return result


def _identifier_values(values: tuple[Identifier, ...]) -> list[str]:
    return [str(value) for value in values]


def _payload(record: PersistedRecord) -> dict[str, Any]:
    if isinstance(record, SourceRecord):
        return {
            "identifier": str(record.identifier),
            "publisher": record.publisher,
            "canonical_url": record.canonical_url,
            "discovery_url": record.discovery_url,
            "dataset_identifier": str(record.dataset_identifier),
            "retrieved_at": _timestamp_payload(record.retrieved_at),
            "version_or_as_of": record.version_or_as_of,
            "geography": record.geography,
            "units": list(record.units),
            "cadence": record.cadence,
            "coverage": record.coverage,
            "access_terms": record.access_terms,
            "quality_status": record.quality_status,
            "allowed_uses": list(record.allowed_uses),
            "prohibited_uses": list(record.prohibited_uses),
        }
    if isinstance(record, RawSnapshot):
        return {
            "identifier": str(record.identifier),
            "sha256": str(record.sha256),
            "byte_length": record.byte_length,
            "media_type": record.media_type,
            "storage_uri": record.storage_uri,
            "received_at": _timestamp_payload(record.received_at),
        }
    if isinstance(record, DatasetVersion):
        return {
            "identifier": str(record.identifier),
            "source_record_id": str(record.source_record_id),
            "raw_snapshot_id": str(record.raw_snapshot_id),
            "schema_version": record.schema_version,
            "status": record.status.value,
            "valid_record_count": record.valid_record_count,
            "rejected_record_count": record.rejected_record_count,
            "temporal_coverage": record.temporal_coverage,
            "geographic_coverage": record.geographic_coverage,
            "as_of_date": record.as_of_date.isoformat(),
            "diagnostic_ids": _identifier_values(record.diagnostic_ids),
            "processing_duration": str(record.processing_duration.value),
            "download_duration": (
                str(record.download_duration.value) if record.download_duration else None
            ),
        }
    if isinstance(record, NormalizedRecord):
        return {
            "identifier": str(record.identifier),
            "dataset_version_id": str(record.dataset_version_id),
            "record_key": record.record_key,
            "source_locator": record.source_locator,
            "timestamp": _timestamp_payload(record.timestamp),
            "value": str(record.value.value),
            "canonical_unit": record.canonical_unit.value,
            "quality_flags": list(record.quality_flags),
        }
    return {
        "identifier": str(record.identifier),
        "normalized_record_id": str(record.normalized_record_id),
        "dataset_version_id": str(record.dataset_version_id),
        "snapshot_hash": str(record.snapshot_hash),
        "source_record_id": str(record.source_record_id),
        "source_locator": record.source_locator,
    }


def _decode(record_type: type[RecordT], value: dict[str, Any]) -> RecordT:
    if record_type is SourceRecord:
        record: PersistedRecord = SourceRecord(
            Identifier(value["identifier"]),
            value["publisher"],
            value["canonical_url"],
            value["discovery_url"],
            Identifier(value["dataset_identifier"]),
            _timestamp(value["retrieved_at"]),
            value["version_or_as_of"],
            value["geography"],
            tuple(value["units"]),
            value["cadence"],
            value["coverage"],
            value["access_terms"],
            value["quality_status"],
            tuple(value["allowed_uses"]),
            tuple(value["prohibited_uses"]),
        )
    elif record_type is RawSnapshot:
        record = RawSnapshot(
            Identifier(value["identifier"]),
            Sha256Digest(value["sha256"]),
            value["byte_length"],
            value["media_type"],
            value["storage_uri"],
            _timestamp(value["received_at"]),
        )
    elif record_type is DatasetVersion:
        record = DatasetVersion(
            Identifier(value["identifier"]),
            Identifier(value["source_record_id"]),
            Identifier(value["raw_snapshot_id"]),
            value["schema_version"],
            DatasetStatus(value["status"]),
            value["valid_record_count"],
            value["rejected_record_count"],
            value["temporal_coverage"],
            value["geographic_coverage"],
            date.fromisoformat(value["as_of_date"]),
            tuple(Identifier(item) for item in value["diagnostic_ids"]),
            Duration(Decimal(value["processing_duration"]), Unit.HOUR),
            (
                Duration(Decimal(value["download_duration"]), Unit.HOUR)
                if value["download_duration"] is not None
                else None
            ),
        )
    elif record_type is NormalizedRecord:
        record = NormalizedRecord(
            Identifier(value["identifier"]),
            Identifier(value["dataset_version_id"]),
            value["record_key"],
            value["source_locator"],
            _timestamp(value["timestamp"]),
            FiniteNumber(Decimal(value["value"])),
            Unit(value["canonical_unit"]),
            tuple(value["quality_flags"]),
        )
    elif record_type is ProvenanceEdge:
        record = ProvenanceEdge(
            Identifier(value["identifier"]),
            Identifier(value["normalized_record_id"]),
            Identifier(value["dataset_version_id"]),
            Sha256Digest(value["snapshot_hash"]),
            Identifier(value["source_record_id"]),
            value["source_locator"],
        )
    else:
        raise TypeError(f"unsupported record type: {record_type!r}")
    return cast(RecordT, record)


class SQLiteAppendOnlyRepository(Generic[RecordT]):
    """Persist one supported record type without update or delete operations."""

    def __init__(self, database_path: Path, record_type: type[RecordT]) -> None:
        if record_type not in _RECORD_TABLES:
            raise TypeError(f"unsupported record type: {record_type!r}")
        self._path = database_path.resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists() and not self._path.is_file():
            raise ValueError("SQLite database path must be a local file")
        self._record_type = record_type
        self._table = _RECORD_TABLES[record_type]
        with self._connect() as connection:
            connection.executescript(_SCHEMA)
            for table in _RECORD_TABLES.values():
                connection.execute(
                    f"""CREATE TRIGGER IF NOT EXISTS {table}_no_update
                    BEFORE UPDATE ON {table} BEGIN
                        SELECT RAISE(ABORT, 'append-only table');
                    END"""
                )
                connection.execute(
                    f"""CREATE TRIGGER IF NOT EXISTS {table}_no_delete
                    BEFORE DELETE ON {table} BEGIN
                        SELECT RAISE(ABORT, 'append-only table');
                    END"""
                )

    def add(self, record: RecordT) -> None:
        if type(record) is not self._record_type:
            raise TypeError(f"repository accepts only {self._record_type.__name__}")
        payload = _payload(record)
        columns: dict[str, str] = {"identifier": str(record.identifier)}
        if isinstance(record, RawSnapshot):
            columns["sha256"] = str(record.sha256)
        elif isinstance(record, DatasetVersion):
            columns.update(
                source_record_id=str(record.source_record_id),
                raw_snapshot_id=str(record.raw_snapshot_id),
            )
        elif isinstance(record, NormalizedRecord):
            columns["dataset_version_id"] = str(record.dataset_version_id)
        elif isinstance(record, ProvenanceEdge):
            columns.update(
                normalized_record_id=str(record.normalized_record_id),
                dataset_version_id=str(record.dataset_version_id),
                snapshot_hash=str(record.snapshot_hash),
                source_record_id=str(record.source_record_id),
            )
        columns["payload"] = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        names = ", ".join(columns)
        placeholders = ", ".join("?" for _ in columns)
        try:
            with self._connect() as connection:
                if isinstance(record, ProvenanceEdge):
                    lineage = connection.execute(
                        """SELECT 1
                        FROM normalized_records AS normalized
                        JOIN dataset_versions AS dataset
                            ON dataset.identifier = normalized.dataset_version_id
                        JOIN raw_snapshots AS snapshot
                            ON snapshot.identifier = dataset.raw_snapshot_id
                        WHERE normalized.identifier = ?
                          AND normalized.dataset_version_id = ?
                          AND dataset.source_record_id = ?
                          AND snapshot.sha256 = ?
                          AND json_extract(normalized.payload, '$.source_locator') = ?""",
                        (
                            str(record.normalized_record_id),
                            str(record.dataset_version_id),
                            str(record.source_record_id),
                            str(record.snapshot_hash),
                            record.source_locator,
                        ),
                    ).fetchone()
                    if lineage is None:
                        raise AppendOnlyViolation(
                            "provenance edge does not match immutable history"
                        )
                connection.execute(
                    f"INSERT INTO {self._table} ({names}) VALUES ({placeholders})",
                    tuple(columns.values()),
                )
        except sqlite3.IntegrityError as error:
            raise AppendOnlyViolation(
                "record already exists or references missing immutable history"
            ) from error

    def get(self, identifier: Identifier) -> RecordT | None:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT payload FROM {self._table} WHERE identifier = ?",
                (str(identifier),),
            ).fetchone()
        if row is None:
            return None
        try:
            value = json.loads(row[0])
            if not isinstance(value, dict):
                raise PersistenceIntegrityError("stored record payload is malformed")
            return _decode(self._record_type, value)
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, PersistenceIntegrityError):
                raise
            raise PersistenceIntegrityError("stored record payload is malformed") from error

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection
