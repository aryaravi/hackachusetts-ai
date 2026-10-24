from dataclasses import FrozenInstanceError
import hashlib
from importlib.resources import files
import json
from pathlib import PurePosixPath
from zoneinfo import ZoneInfo

import pytest

from omnigridx.domain import CapabilityStatus
from omnigridx.infrastructure import MASSACHUSETTS_DATA_PACK


_BUNDLED_SNAPSHOT_HASHES = {
    "eia-ma-electricity-profile.json": "9fbeaa424c1877ca49ed5e6feee7648b63c191b121b5dd6f0d1541255da413ae",
    "epa-egrid.json": "5597454fba3a65a6e6e7407d1c1d69490f60061731f94868f9f68ed0e0387a55",
    "hifld-transmission-lines-ma.json": "8a5983687178b7efb24526b3f74fc9acd1a6e2983b12908ad9c36edcc03c4e87",
    "iso-ne-load-demand.json": "6f42d93be452f1f5df7ff1b58b10b66d36dc41e74405ada5bf90c8f158524c5c",
    "ma-berdo-2021.json": "da3a56789577d04e4d961bd6f2de717b4566bc8996cc7f35c97c165217600436",
    "ma-climate-assessment.json": "116b63f652f62f48e758d31eb4cd9b7d4bc8a5803921f7f5710ff7aee918cca7",
    "ma-electric-rates-tariffs.json": "82065d5310eb47599c53443c86ec5262cc354ed01bd8128be95f778b378b6ba6",
    "ma-electric-utility-by-town.json": "66d78da16789ad6d20809ee680512d032a626545d1aefd601c6e11f271a1a816",
    "ma-energy-data.json": "d826089a56100740eabd0593b707e723f59d903d361a6b6de422a49a29f3b430",
    "ma-landfill-renewables.json": "6b202a92559f24582ded6d19bda7d0554a044344e583a07d707ca8c374d901bb",
    "nrel-nsrdb.json": "4edf330756f072c89acb5d1c9cfae845243547fcc9129565cf483d4153fc3fed",
    "nws-api.json": "264cf933cb4ebcce31117dbbd87359819a049a1a8a2a70605edd9487688ebbc2",
    "resilientmass.json": "af69bed14697edb3b55020224175054cfe37e7afc4ba84cd2cc62dc86f69c5a7",
}


def test_massachusetts_pack_has_versioned_reference_schema() -> None:
    pack = MASSACHUSETTS_DATA_PACK

    assert (pack.identity.name, pack.identity.version, pack.schema_version) == (
        "Massachusetts_Data_Pack",
        "2026.1",
        "1.0",
    )
    assert pack.state_code == "MA"
    assert pack.time_zone_name == "America/New_York"
    assert ZoneInfo(pack.time_zone_name).key == pack.time_zone_name
    assert pack.billing_calendar.time_zone_name == pack.time_zone_name
    assert pack.geography_mappings[0].source_fields == ("TOWN", "ELEC", "ELEC_LABEL")
    assert pack.emissions_factor_references[0].source_record_id.value == "epa-egrid"
    with pytest.raises(FrozenInstanceError):
        pack.state_code = "NY"  # type: ignore[misc]


def test_approved_sources_use_versioned_local_metadata_and_publisher_urls() -> None:
    pack = MASSACHUSETTS_DATA_PACK

    assert len(pack.sources) == 13
    assert {declaration.snapshot_version for declaration in pack.sources} == {"2026.1"}
    assert all(declaration.local_uri.startswith("local://") for declaration in pack.sources)
    assert all(declaration.source.canonical_url.startswith("https://") for declaration in pack.sources)
    assert all(
        declaration.source.discovery_url
        == "https://hackachusetts2026.vercel.app/#/climate"
        for declaration in pack.sources
    )
    assert all(
        declaration.source.canonical_url != declaration.source.discovery_url
        for declaration in pack.sources
    )
    assert all(
        declaration.source.access_terms
        and declaration.source.allowed_uses
        and declaration.source.prohibited_uses
        for declaration in pack.sources
    )
    required_metadata = (
        "publisher",
        "canonical_url",
        "dataset_identifier",
        "retrieved_at",
        "version_or_as_of",
        "geography",
        "units",
        "cadence",
        "coverage",
        "access_terms",
        "quality_status",
        "allowed_uses",
        "prohibited_uses",
    )
    assert all(
        getattr(declaration.source, field)
        for declaration in pack.sources
        for field in required_metadata
    )

    bundled_root = files("omnigridx.infrastructure").joinpath("data")
    for declaration in pack.sources:
        relative_path = PurePosixPath(declaration.local_uri.removeprefix("local://"))
        snapshot = bundled_root.joinpath(*relative_path.parts).read_bytes()
        metadata = json.loads(snapshot)
        assert metadata == {
            "content": "approved source metadata only; source values not bundled",
            "snapshot_version": declaration.snapshot_version,
            "source_id": declaration.source.identifier.value,
        }
        assert hashlib.sha256(snapshot).hexdigest() == _BUNDLED_SNAPSHOT_HASHES[
            relative_path.name
        ]

    categories = {
        category for declaration in pack.sources for category in declaration.categories
    }
    assert {
        "utility_territory",
        "demand_market_context",
        "weather_source",
        "climate_context",
        "emissions_factor",
        "tariff_source",
        "policy_source",
    } <= categories


def test_capabilities_are_explicit_and_live_adapters_are_future_work() -> None:
    pack = MASSACHUSETTS_DATA_PACK
    capabilities = {item.name: item.status for item in pack.capabilities}

    assert capabilities["utility_territory_lookup"] is CapabilityStatus.SUPPORTED
    assert capabilities["customer_site_load"] is CapabilityStatus.UNSUPPORTED
    assert capabilities["verified_tariff_configuration"] is CapabilityStatus.UNSUPPORTED
    assert capabilities["feeder_capacity"] is CapabilityStatus.UNSUPPORTED
    assert capabilities["live_source_adapters"] is CapabilityStatus.FUTURE_CAPABILITY
    assert pack.live_adapter_milestone.startswith("Production:")
