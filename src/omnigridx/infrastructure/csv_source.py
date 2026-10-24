"""CSV adapter for immutable local source snapshots."""

import csv
import io
from collections.abc import Iterable

from omnigridx.domain.records import SourceRecord

_REQUIRED_FIELDS = {"record_key", "timestamp", "value", "unit", "geography"}


class LocalCsvSourceAdapter:
    """Parse the minimal normalized-input CSV shape without altering source bytes."""

    def parse(
        self, raw: bytes, source: SourceRecord
    ) -> Iterable[dict[str, str | None]]:
        del source
        try:
            stream = io.StringIO(raw.decode("utf-8-sig"), newline="")
            reader = csv.DictReader(stream, strict=True)
            fields = set(reader.fieldnames or ())
            missing = sorted(_REQUIRED_FIELDS - fields)
            if missing:
                raise ValueError(f"missing CSV fields: {', '.join(missing)}")
            for row in reader:
                yield dict(row)
        except (UnicodeDecodeError, csv.Error) as error:
            raise ValueError(f"invalid CSV snapshot: {error}") from error
