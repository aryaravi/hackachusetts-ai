from dataclasses import replace
from pathlib import Path

import pytest

from omnigridx.domain import Sha256Digest
from omnigridx.infrastructure import LocalSnapshotRepository, SnapshotIntegrityError


def test_snapshot_is_written_once_by_computed_hash_and_read_verified(tmp_path: Path) -> None:
    objects = tmp_path / "objects"
    repository = LocalSnapshotRepository(objects)

    first = repository.put_once(b"immutable source bytes", "text/csv")
    second = repository.put_once(b"immutable source bytes", "text/csv")

    assert first == second
    assert repository.get_verified(first) == b"immutable source bytes"
    assert [path.name for path in objects.iterdir()] == [str(first.sha256)]


def test_snapshot_read_rejects_tampered_bytes_and_mismatched_metadata(tmp_path: Path) -> None:
    objects = tmp_path / "objects"
    repository = LocalSnapshotRepository(objects)
    snapshot = repository.put_once(b"original", "application/octet-stream")

    with pytest.raises(SnapshotIntegrityError, match="storage URI"):
        repository.get_verified(replace(snapshot, sha256=Sha256Digest("a" * 64)))

    (objects / str(snapshot.sha256)).write_bytes(b"tampered")
    with pytest.raises(SnapshotIntegrityError, match="hash and length"):
        repository.get_verified(snapshot)
    with pytest.raises(SnapshotIntegrityError, match="hash and length"):
        repository.put_once(b"original", "application/octet-stream")
