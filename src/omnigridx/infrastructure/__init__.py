"""Infrastructure adapters and bundled reference data."""

from .csv_source import LocalCsvSourceAdapter
from .massachusetts_pack import MASSACHUSETTS_DATA_PACK
from .sample import SAMPLE_DATASET_ID, build_sample_report
from .scipy_solver import ScipyMilpSolver
from .snapshots import LocalSnapshotRepository, SnapshotIntegrityError
from .sqlite import (
    AppendOnlyViolation,
    PersistenceIntegrityError,
    SQLiteAppendOnlyRepository,
)

__all__ = [
    "AppendOnlyViolation",
    "LocalCsvSourceAdapter",
    "LocalSnapshotRepository",
    "MASSACHUSETTS_DATA_PACK",
    "SAMPLE_DATASET_ID",
    "build_sample_report",
    "PersistenceIntegrityError",
    "ScipyMilpSolver",
    "SQLiteAppendOnlyRepository",
    "SnapshotIntegrityError",
]
