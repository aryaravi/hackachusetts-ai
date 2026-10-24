"""Immutable records for reproducible OmniGridX runs."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
import re
from typing import Any

from .values import CapabilityStatus, Duration, Energy, FiniteNumber, Identifier, Interval, Timestamp, Unit

_SHA256 = re.compile(r"[0-9a-f]{64}").fullmatch


class AlternativeType(StrEnum):
    EXISTING = "existing"
    RULE_BASED = "rule_based"
    OPTIMIZED = "optimized"


class DatasetStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ScenarioStatus(StrEnum):
    VALID = "valid"
    REJECTED = "rejected"


class RunStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Sha256Digest:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or _SHA256(self.value) is None:
            raise ValueError("SHA-256 digest must be 64 lowercase hexadecimal characters")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class VersionReference:
    name: str
    version: str


@dataclass(frozen=True, slots=True)
class NamedHash:
    name: str
    digest: Sha256Digest


@dataclass(frozen=True, slots=True)
class ManifestDecimal:
    name: str
    value: FiniteNumber
    unit: str

    def __post_init__(self) -> None:
        if not self.name or not self.unit:
            raise ValueError("manifest decimals require a name and explicit unit")


@dataclass(frozen=True, slots=True)
class SourceRecord:
    identifier: Identifier
    publisher: str
    canonical_url: str
    discovery_url: str | None
    dataset_identifier: Identifier
    retrieved_at: Timestamp
    version_or_as_of: str
    geography: str
    units: tuple[str, ...]
    cadence: str
    coverage: str
    access_terms: str
    quality_status: str
    allowed_uses: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RawSnapshot:
    identifier: Identifier
    sha256: Sha256Digest
    byte_length: int
    media_type: str
    storage_uri: str
    received_at: Timestamp


@dataclass(frozen=True, slots=True)
class DatasetVersion:
    identifier: Identifier
    source_record_id: Identifier
    raw_snapshot_id: Identifier
    schema_version: str
    status: DatasetStatus
    valid_record_count: int
    rejected_record_count: int
    temporal_coverage: str
    geographic_coverage: str
    as_of_date: date
    diagnostic_ids: tuple[Identifier, ...]
    processing_duration: Duration
    download_duration: Duration | None


@dataclass(frozen=True, slots=True)
class NormalizedRecord:
    identifier: Identifier
    dataset_version_id: Identifier
    record_key: str
    source_locator: str
    timestamp: Timestamp
    value: FiniteNumber
    canonical_unit: Unit
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProvenanceEdge:
    identifier: Identifier
    normalized_record_id: Identifier
    dataset_version_id: Identifier
    snapshot_hash: Sha256Digest
    source_record_id: Identifier
    source_locator: str


@dataclass(frozen=True, slots=True)
class ScenarioVersion:
    identifier: Identifier
    tenant_id: Identifier
    site_id: Identifier
    dataset_version_ids: tuple[Identifier, ...]
    pack: VersionReference
    policy_snapshot: VersionReference
    tariff_configuration: VersionReference
    intervals: tuple[Interval, ...]
    parameters: tuple[ManifestDecimal, ...]
    assumptions: tuple[str, ...]
    exclusions: tuple[str, ...]
    status: ScenarioStatus


@dataclass(frozen=True, slots=True)
class IntervalResult:
    run_id: Identifier
    alternative_type: AlternativeType
    interval_id: Identifier
    generation_available: Energy
    generation_dispatched: Energy
    generation_curtailed: Energy
    grid_import: Energy
    grid_export: Energy
    battery_charge: Energy
    battery_discharge: Energy
    served_critical_load: Energy
    served_noncritical_load: Energy
    critical_unserved_load: Energy
    noncritical_unserved_load: Energy
    other_conversion_loss: Energy
    storage_conversion_loss: Energy
    state_of_charge_start: Energy
    state_of_charge_end: Energy
    constraint_check_passed: bool


@dataclass(frozen=True, slots=True)
class Schedule:
    identifier: Identifier
    scenario_version_id: Identifier
    alternative_type: AlternativeType
    intervals: tuple[IntervalResult, ...]

    def __post_init__(self) -> None:
        interval_ids = tuple(value.interval_id for value in self.intervals)
        if not interval_ids or len(set(interval_ids)) != len(interval_ids):
            raise ValueError("schedule requires unique interval results")
        if any(value.alternative_type is not self.alternative_type for value in self.intervals):
            raise ValueError("schedule interval alternative types must match")


@dataclass(frozen=True, slots=True)
class ResultMetric:
    name: str
    value: FiniteNumber | None
    unit: str


@dataclass(frozen=True, slots=True)
class AlternativeResult:
    identifier: Identifier
    run_id: Identifier
    alternative_type: AlternativeType
    schedule_id: Identifier
    metrics: tuple[ResultMetric, ...]
    objective_components: tuple[ResultMetric, ...]
    solver_outcome: str | None
    checker_report_id: Identifier
    labels: tuple[str, ...]
    disclosures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RunResult:
    identifier: Identifier
    manifest_id: Identifier
    status: RunStatus
    started_at: Timestamp
    completed_at: Timestamp | None
    runtime: Duration | None
    alternative_result_ids: tuple[Identifier, ...]
    diagnostic_ids: tuple[Identifier, ...]


def _decimal_string(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def _timestamp_string(timestamp: Timestamp) -> str:
    return timestamp.instant_utc.isoformat().replace("+00:00", "Z")


def _version(reference: VersionReference) -> dict[str, str]:
    return {"name": reference.name, "version": reference.version}


def _manifest_decimal(value: ManifestDecimal) -> dict[str, str]:
    return {
        "name": value.name,
        "unit": value.unit,
        "value": _decimal_string(value.value.value),
    }


@dataclass(frozen=True, slots=True)
class RunManifest:
    identifier: Identifier
    scenario_version_id: Identifier
    created_at: Timestamp
    alternative_types: tuple[AlternativeType, ...]
    ordered_interval_ids: tuple[Identifier, ...]
    input_hashes: tuple[NamedHash, ...]
    source_record_ids: tuple[Identifier, ...]
    pack: VersionReference
    policy_snapshot: VersionReference
    tariff_configuration: VersionReference
    calculation_code: VersionReference
    dependencies: tuple[VersionReference, ...]
    solver: VersionReference
    solver_settings: tuple[ManifestDecimal, ...]
    tolerances: tuple[ManifestDecimal, ...]
    random_seed: int
    deployment_mode: str
    capability_mode: CapabilityStatus

    def __post_init__(self) -> None:
        expected = (
            AlternativeType.EXISTING,
            AlternativeType.RULE_BASED,
            AlternativeType.OPTIMIZED,
        )
        if self.alternative_types != expected:
            raise ValueError("run manifest must contain exactly existing, rule_based, and optimized")
        if not self.ordered_interval_ids or len(set(self.ordered_interval_ids)) != len(
            self.ordered_interval_ids
        ):
            raise ValueError("run manifest requires unique ordered interval IDs")
        for values in (
            self.input_hashes,
            self.dependencies,
            self.solver_settings,
            self.tolerances,
        ):
            names = tuple(value.name for value in values)
            if len(set(names)) != len(names):
                raise ValueError("manifest named fields must be unique")
        if not self.deployment_mode:
            raise ValueError("deployment mode is required")

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "alternative_types": [value.value for value in self.alternative_types],
            "calculation_code": _version(self.calculation_code),
            "capability_mode": self.capability_mode.value,
            "created_at_utc": _timestamp_string(self.created_at),
            "dependencies": [
                _version(value) for value in sorted(self.dependencies, key=lambda item: item.name)
            ],
            "deployment_mode": self.deployment_mode,
            "identifier": str(self.identifier),
            "input_hashes": [
                {"name": value.name, "sha256": str(value.digest)}
                for value in sorted(self.input_hashes, key=lambda item: item.name)
            ],
            "ordered_interval_ids": [str(value) for value in self.ordered_interval_ids],
            "pack": _version(self.pack),
            "policy_snapshot": _version(self.policy_snapshot),
            "random_seed": str(self.random_seed),
            "scenario_version_id": str(self.scenario_version_id),
            "solver": _version(self.solver),
            "solver_settings": [
                _manifest_decimal(value)
                for value in sorted(self.solver_settings, key=lambda item: item.name)
            ],
            "source_record_ids": sorted(str(value) for value in self.source_record_ids),
            "tariff_configuration": _version(self.tariff_configuration),
            "tolerances": [
                _manifest_decimal(value)
                for value in sorted(self.tolerances, key=lambda item: item.name)
            ],
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @property
    def fingerprint(self) -> Sha256Digest:
        digest = hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
        return Sha256Digest(digest)
