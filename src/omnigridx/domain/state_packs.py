"""Immutable metadata schema for state data packs."""

from dataclasses import dataclass

from .records import SourceRecord, VersionReference
from .values import CapabilityStatus, Identifier


@dataclass(frozen=True, slots=True)
class BillingCalendar:
    name: str
    time_zone_name: str
    period_convention: str
    boundary_time_local: str


@dataclass(frozen=True, slots=True)
class SnapshotSourceDeclaration:
    source: SourceRecord
    categories: tuple[str, ...]
    snapshot_version: str
    local_uri: str


@dataclass(frozen=True, slots=True)
class GeographyMapping:
    name: str
    source_record_id: Identifier
    source_fields: tuple[str, ...]
    canonical_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EmissionsFactorReference:
    name: str
    source_record_id: Identifier
    geography: str
    classification: str
    numerator_unit: str
    denominator_unit: str


@dataclass(frozen=True, slots=True)
class CapabilityDeclaration:
    name: str
    status: CapabilityStatus
    reason: str


@dataclass(frozen=True, slots=True)
class StateDataPackDefinition:
    identity: VersionReference
    schema_version: str
    state_code: str
    time_zone_name: str
    billing_calendar: BillingCalendar
    sources: tuple[SnapshotSourceDeclaration, ...]
    geography_mappings: tuple[GeographyMapping, ...]
    emissions_factor_references: tuple[EmissionsFactorReference, ...]
    capabilities: tuple[CapabilityDeclaration, ...]
    live_adapter_milestone: str
