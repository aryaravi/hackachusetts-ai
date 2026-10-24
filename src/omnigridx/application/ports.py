"""Narrow in-process boundaries implemented by application infrastructure."""

from collections.abc import Iterable, Sequence
from typing import Protocol, TypeVar

from omnigridx.domain.records import IntervalResult, RawSnapshot, SourceRecord
from omnigridx.domain.values import Identifier

RecordT = TypeVar("RecordT")
ModelT = TypeVar("ModelT", contravariant=True)
ResultT = TypeVar("ResultT", covariant=True)
ParsedT = TypeVar("ParsedT", covariant=True)
CalculationT = TypeVar("CalculationT", covariant=True)
ContextT = TypeVar("ContextT", contravariant=True)
ResolvedT = TypeVar("ResolvedT", covariant=True)


class AppendOnlyRepository(Protocol[RecordT]):
    def add(self, record: RecordT) -> None: ...

    def get(self, identifier: Identifier) -> RecordT | None: ...


class SnapshotRepository(Protocol):
    def put_once(self, content: bytes, media_type: str) -> RawSnapshot: ...

    def get_verified(self, snapshot: RawSnapshot) -> bytes: ...


class SolverPort(Protocol[ModelT, ResultT]):
    def solve(self, model: ModelT) -> ResultT: ...


class TariffAdapter(Protocol[CalculationT]):
    def calculate(self, intervals: Sequence[IntervalResult]) -> CalculationT: ...


class SourceAdapter(Protocol[ParsedT]):
    def parse(self, raw: bytes, source: SourceRecord) -> Iterable[ParsedT]: ...


class StateDataPack(Protocol[ContextT, ResolvedT]):
    def validate(self, snapshot_repository: SnapshotRepository) -> tuple[str, ...]: ...

    def resolve(self, capability: str, context: ContextT) -> ResolvedT: ...
