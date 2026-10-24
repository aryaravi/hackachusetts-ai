"""Local immutable content-addressed snapshot storage."""

from datetime import UTC, datetime
import hashlib
import os
from pathlib import Path
import tempfile

from omnigridx.domain.records import RawSnapshot, Sha256Digest
from omnigridx.domain.values import Identifier, Timestamp


class SnapshotIntegrityError(ValueError):
    """Stored snapshot bytes do not match their immutable metadata."""


class LocalSnapshotRepository:
    """Store immutable objects by their computed SHA-256 digest."""

    def __init__(self, object_directory: Path) -> None:
        self._directory = object_directory.resolve()
        self._directory.mkdir(parents=True, exist_ok=True)
        if not self._directory.is_dir():
            raise ValueError("snapshot object directory must be a directory")

    def put_once(self, content: bytes, media_type: str) -> RawSnapshot:
        if not isinstance(content, bytes):
            raise TypeError("snapshot content must be bytes")
        if not media_type:
            raise ValueError("snapshot media type is required")

        digest = hashlib.sha256(content).hexdigest()
        destination = self._directory / digest
        if destination.exists():
            self._verify_path(destination, digest, len(content))
        else:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".snapshot-", dir=self._directory
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, destination)
                directory_descriptor = os.open(self._directory, os.O_RDONLY)
                try:
                    os.fsync(directory_descriptor)
                finally:
                    os.close(directory_descriptor)
            finally:
                temporary.unlink(missing_ok=True)

        self._verify_path(destination, digest, len(content))
        stat = destination.stat()
        return RawSnapshot(
            identifier=Identifier(digest),
            sha256=Sha256Digest(digest),
            byte_length=stat.st_size,
            media_type=media_type,
            storage_uri=destination.as_uri(),
            received_at=Timestamp(datetime.fromtimestamp(stat.st_mtime, tz=UTC)),
        )

    def get_verified(self, snapshot: RawSnapshot) -> bytes:
        expected_path = self._directory / str(snapshot.sha256)
        if snapshot.storage_uri != expected_path.as_uri():
            raise SnapshotIntegrityError("snapshot storage URI does not match its hash")
        content = expected_path.read_bytes()
        self._verify_content(content, str(snapshot.sha256), snapshot.byte_length)
        return content

    @staticmethod
    def _verify_path(path: Path, digest: str, byte_length: int) -> None:
        LocalSnapshotRepository._verify_content(path.read_bytes(), digest, byte_length)

    @staticmethod
    def _verify_content(content: bytes, digest: str, byte_length: int) -> None:
        if len(content) != byte_length or hashlib.sha256(content).hexdigest() != digest:
            raise SnapshotIntegrityError("snapshot content does not match its hash and length")
