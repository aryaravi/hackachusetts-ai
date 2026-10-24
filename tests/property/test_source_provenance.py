from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings, strategies as st

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
from omnigridx.infrastructure import LocalSnapshotRepository, SQLiteAppendOnlyRepository


# Feature: omnigridx, Property 10: Source provenance is complete and authoritative
# **Validates: Requirements 1.3, 1.7, 1.13**
@given(
    content=st.binary(min_size=1, max_size=512),
    publisher_slug=st.text(
        alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
        min_size=1,
        max_size=12,
    ),
    values=st.lists(
        st.decimals(
            min_value=Decimal("-1000000"),
            max_value=Decimal("1000000"),
            places=3,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=1,
        max_size=6,
    ),
)
@settings(max_examples=100, deadline=None)
def test_source_provenance_is_complete_and_authoritative(
    content: bytes, publisher_slug: str, values: list[Decimal]
) -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        database = root / "metadata.sqlite3"
        snapshots = LocalSnapshotRepository(root / "objects")
        snapshot = snapshots.put_once(content, "application/octet-stream")
        source = SourceRecord(
            identifier=Identifier("source-1"),
            publisher=f"{publisher_slug} authoritative publisher",
            canonical_url=f"https://{publisher_slug}.publisher.example/data",
            discovery_url="https://hackachusetts2026.vercel.app/#/climate",
            dataset_identifier=Identifier(f"{publisher_slug}-dataset"),
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
        dataset = DatasetVersion(
            identifier=Identifier("dataset-1"),
            source_record_id=source.identifier,
            raw_snapshot_id=snapshot.identifier,
            schema_version="1",
            status=DatasetStatus.ACCEPTED,
            valid_record_count=len(values),
            rejected_record_count=0,
            temporal_coverage="2026-01-01/2026-01-31",
            geographic_coverage="Massachusetts",
            as_of_date=date(2026, 1, 31),
            diagnostic_ids=(),
            processing_duration=Duration(Decimal("0.001"), Unit.HOUR),
            download_duration=None,
        )

        sources = SQLiteAppendOnlyRepository(database, SourceRecord)
        raw_snapshots = SQLiteAppendOnlyRepository(database, RawSnapshot)
        datasets = SQLiteAppendOnlyRepository(database, DatasetVersion)
        records = SQLiteAppendOnlyRepository(database, NormalizedRecord)
        edges = SQLiteAppendOnlyRepository(database, ProvenanceEdge)
        sources.add(source)
        raw_snapshots.add(snapshot)
        datasets.add(dataset)

        for index, value in enumerate(values):
            locator = f"row:{index + 1}"
            record = NormalizedRecord(
                identifier=Identifier(f"record-{index}"),
                dataset_version_id=dataset.identifier,
                record_key=f"interval-{index}",
                source_locator=locator,
                timestamp=Timestamp(
                    datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * index)
                ),
                value=FiniteNumber(value),
                canonical_unit=Unit.KILOWATT_HOUR,
                quality_flags=("accepted",),
            )
            edge = ProvenanceEdge(
                identifier=Identifier(f"edge-{index}"),
                normalized_record_id=record.identifier,
                dataset_version_id=dataset.identifier,
                snapshot_hash=snapshot.sha256,
                source_record_id=source.identifier,
                source_locator=locator,
            )
            records.add(record)
            edges.add(edge)

            stored_record = records.get(record.identifier)
            stored_edge = edges.get(edge.identifier)
            assert stored_record == record
            assert stored_edge is not None
            assert stored_edge.normalized_record_id == stored_record.identifier
            assert stored_edge.dataset_version_id == stored_record.dataset_version_id
            assert stored_edge.source_locator == stored_record.source_locator
            assert stored_edge.source_record_id == source.identifier
            assert stored_edge.snapshot_hash == snapshot.sha256

        stored_source = sources.get(source.identifier)
        stored_dataset = datasets.get(dataset.identifier)
        stored_snapshot = raw_snapshots.get(snapshot.identifier)
        assert stored_source == source
        assert stored_dataset == dataset
        assert stored_snapshot == snapshot
        assert stored_source is not None
        assert all(
            (
                stored_source.publisher,
                stored_source.canonical_url,
                stored_source.dataset_identifier.value,
                stored_source.version_or_as_of,
                stored_source.geography,
                stored_source.units,
                stored_source.cadence,
                stored_source.coverage,
                stored_source.access_terms,
                stored_source.quality_status,
                stored_source.allowed_uses,
                stored_source.prohibited_uses,
            )
        )
        assert stored_source.canonical_url != stored_source.discovery_url
        assert snapshots.get_verified(snapshot) == content
        assert hashlib.sha256(content).hexdigest() == str(snapshot.sha256)
