"""Fail-closed deployment and data-use decisions."""

from dataclasses import dataclass
from enum import StrEnum
from ipaddress import ip_address

from omnigridx.domain import CapabilityStatus


class DataSourceKind(StrEnum):
    BUNDLED_SAMPLE = "bundled_sample"
    AUTHORIZED_CUSTOMER_DATA = "Authorized_Customer_Data"
    PUBLIC = "public"
    ZONAL = "zonal"


class ConclusionKind(StrEnum):
    SITE_LOAD = "site_load"
    TARIFF = "tariff"
    CONTEXT = "context"


class ReleaseCapability(StrEnum):
    FIRST_RELEASE_SCREENING = "first_release_screening"
    BUNDLED_SAMPLE_SCREENING = "bundled_sample_screening"
    DATA_CENTER_LOAD_SAMPLE = "data_center_load_sample"
    LIVE_SOURCE_ADAPTERS = "live_source_adapters"
    OPERATIONAL_ML_FORECAST = "operational_ml_forecast"
    BROAD_POLICY_INTELLIGENCE = "broad_policy_intelligence"
    BESPOKE_DATA_CENTER_THERMAL_MODELING = "bespoke_data_center_thermal_modeling"


_CAPABILITY_STATUSES = {
    ReleaseCapability.FIRST_RELEASE_SCREENING: CapabilityStatus.SUPPORTED,
    ReleaseCapability.BUNDLED_SAMPLE_SCREENING: CapabilityStatus.HACKATHON_DEMO,
    ReleaseCapability.DATA_CENTER_LOAD_SAMPLE: CapabilityStatus.HACKATHON_DEMO,
    ReleaseCapability.LIVE_SOURCE_ADAPTERS: CapabilityStatus.FUTURE_CAPABILITY,
    ReleaseCapability.OPERATIONAL_ML_FORECAST: CapabilityStatus.FUTURE_CAPABILITY,
    ReleaseCapability.BROAD_POLICY_INTELLIGENCE: CapabilityStatus.FUTURE_CAPABILITY,
    ReleaseCapability.BESPOKE_DATA_CENTER_THERMAL_MODELING: CapabilityStatus.FUTURE_CAPABILITY,
}


@dataclass(frozen=True, slots=True)
class GateDecision:
    allowed: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DemoLocalSettings:
    bind_host: str
    dataset_ids: tuple[str, ...]
    uploads_enabled: bool = False
    remote_adapters_enabled: bool = False
    customer_data_enabled: bool = False


@dataclass(frozen=True, slots=True)
class DemoPublicSettings:
    bind_host: str
    port: int
    dataset_ids: tuple[str, ...]
    uploads_enabled: bool = False
    arbitrary_sources_enabled: bool = False
    remote_adapters_enabled: bool = False
    customer_data_enabled: bool = False
    deferred_operations_enabled: bool = False
    deferred_runtime_imports_enabled: bool = False
    workers: int = 1
    persistent_storage_enabled: bool = False
    response_visible_secret_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CapabilityGate:
    bundled_sample_dataset_ids: frozenset[str]

    def __post_init__(self) -> None:
        if not self.bundled_sample_dataset_ids or any(
            not dataset_id for dataset_id in self.bundled_sample_dataset_ids
        ):
            raise ValueError("bundled sample dataset IDs must be nonempty")

    def validate_demo_local_startup(self, settings: DemoLocalSettings) -> GateDecision:
        reasons: list[str] = []
        try:
            loopback = ip_address(settings.bind_host).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            reasons.append("demo-local must bind to a loopback IP address")
        if not settings.dataset_ids:
            reasons.append("demo-local requires at least one bundled sample dataset")
        unknown_ids = sorted(set(settings.dataset_ids) - self.bundled_sample_dataset_ids)
        if unknown_ids:
            reasons.append(f"datasets are not bundled samples: {', '.join(unknown_ids)}")
        if settings.uploads_enabled:
            reasons.append("uploads must be disabled in demo-local")
        if settings.remote_adapters_enabled:
            reasons.append("remote adapters must be disabled in demo-local")
        if settings.customer_data_enabled:
            reasons.append("customer data must be disabled in demo-local")
        return GateDecision(not reasons, tuple(reasons))

    def validate_demo_public_startup(self, settings: DemoPublicSettings) -> GateDecision:
        reasons: list[str] = []
        if settings.bind_host not in {"0.0.0.0", "::"}:
            reasons.append("demo-public must use the platform bind host")
        if isinstance(settings.port, bool) or not 0 < settings.port < 65536:
            reasons.append("demo-public requires a valid platform port")
        if not settings.dataset_ids:
            reasons.append("demo-public requires a bundled sample dataset")
        unknown_ids = sorted(set(settings.dataset_ids) - self.bundled_sample_dataset_ids)
        if unknown_ids:
            reasons.append(f"datasets are not bundled samples: {', '.join(unknown_ids)}")
        restricted = {
            "uploads": settings.uploads_enabled,
            "arbitrary source registration": settings.arbitrary_sources_enabled,
            "remote adapters": settings.remote_adapters_enabled,
            "customer data": settings.customer_data_enabled,
            "deferred operations": settings.deferred_operations_enabled,
            "deferred runtime imports": settings.deferred_runtime_imports_enabled,
            "persistent storage": settings.persistent_storage_enabled,
        }
        reasons.extend(
            f"{name} must be disabled in demo-public"
            for name, enabled in restricted.items()
            if enabled
        )
        if settings.workers != 1:
            reasons.append("demo-public must use exactly one in-memory worker")
        if settings.response_visible_secret_names:
            reasons.append("secrets must never be visible in responses")
        return GateDecision(not reasons, tuple(reasons))

    def admit_demo_local_data(
        self, dataset_id: str, source_kind: DataSourceKind
    ) -> GateDecision:
        if source_kind is not DataSourceKind.BUNDLED_SAMPLE:
            return GateDecision(False, ("demo-local accepts bundled sample data only",))
        if dataset_id not in self.bundled_sample_dataset_ids:
            return GateDecision(False, ("dataset is not an approved bundled sample",))
        return GateDecision(True)

    def authorize_first_release_conclusion(
        self,
        source_kind: DataSourceKind,
        conclusion: ConclusionKind,
        *,
        authorization_recorded: bool,
    ) -> GateDecision:
        if conclusion is ConclusionKind.CONTEXT:
            return GateDecision(True)
        if (
            source_kind is DataSourceKind.AUTHORIZED_CUSTOMER_DATA
            and authorization_recorded
        ):
            return GateDecision(True)
        return GateDecision(
            False,
            (
                "site-load and tariff conclusions require Authorized_Customer_Data",
                "public and zonal sources are contextual only",
            ),
        )

    def capability_status(self, capability: ReleaseCapability) -> CapabilityStatus:
        return _CAPABILITY_STATUSES[capability]
