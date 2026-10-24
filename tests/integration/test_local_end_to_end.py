import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from importlib.resources import files
import json
from pathlib import Path
from typing import Any, cast

import pytest
from starlette.applications import Starlette
from starlette.types import Message

from omnigridx.infrastructure import LocalSnapshotRepository
from omnigridx.infrastructure import sample as sample_module
from omnigridx.web.app import create_app


EXPECTED_REPORT_FINGERPRINT = (
    "692f2d67cf31e8ecad9050f4486b615f0ce586078f78fb865ce8eaf1ded006f3"
)
EXPECTED_METRICS = {
    "clean_energy_share",
    "critical_service_fraction",
    "operating_cost",
    "outage_service",
    "peak_import",
    "purchased_electricity_emissions",
}


@dataclass(frozen=True)
class AsgiResponse:
    status: int
    body: bytes

    def json(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.body))


async def _request(app: Starlette, path: str, method: str = "GET") -> AsgiResponse:
    sent: list[Message] = []
    received = False

    async def receive() -> Message:
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": (),
            "client": ("127.0.0.1", 50000),
            "server": ("127.0.0.1", 8000),
        },
        receive,
        send,
    )
    start = next(message for message in sent if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    return AsgiResponse(start["status"], body)


def _run(
    operation: Callable[[Starlette], Awaitable[tuple[AsgiResponse, ...]]],
) -> tuple[AsgiResponse, ...]:
    async def run_requests() -> tuple[AsgiResponse, ...]:
        app = create_app(environment={"HOST": "127.0.0.1", "PORT": "8000"})
        async with app.router.lifespan_context(app):
            return await operation(app)

    return asyncio.run(run_requests())


def test_bundled_sample_runs_end_to_end_from_temporary_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundled_bytes = (
        files("omnigridx.infrastructure")
        .joinpath("data/sample/judge-scenario-v1.json")
        .read_bytes()
    )
    snapshots = LocalSnapshotRepository(tmp_path / "objects")
    snapshot = snapshots.put_once(bundled_bytes, "application/json")
    monkeypatch.setattr(
        sample_module, "_sample_bytes", lambda: snapshots.get_verified(snapshot)
    )

    async def requests(app: Starlette) -> tuple[AsgiResponse, ...]:
        return (
            await _request(app, "/healthz"),
            await _request(app, "/"),
            await _request(app, "/api/sample-report"),
            await _request(app, "/upload", "POST"),
            await _request(app, "/api/customer-data"),
            await _request(app, "/api/forecasts"),
        )

    health, html, report, upload, customer_data, forecasts = _run(requests)
    document = report.json()

    assert snapshots.get_verified(snapshot) == bundled_bytes
    assert health.status == html.status == report.status == 200
    assert document["report_fingerprint"] == EXPECTED_REPORT_FINGERPRINT
    assert health.json()["report_fingerprint"] == EXPECTED_REPORT_FINGERPRINT
    assert document["label"] == "Fast_Judge_MVP"
    assert [item["alternative"] for item in document["alternatives"]] == [
        "existing",
        "rule_based",
        "optimized",
    ]
    assert [item["solver"]["status"] for item in document["alternatives"]] == [
        "not_applicable",
        "not_applicable",
        "optimal",
    ]

    for alternative in document["alternatives"]:
        metrics = alternative["metrics"]
        assert set(metrics) == EXPECTED_METRICS
        assert alternative["independent_checker"]["status"] == "passed"
        assert alternative["independent_checker"]["diagnostics"] == []
        assert all(
            interval["constraint_check_passed"]
            for interval in alternative["schedule"]["intervals"]
        )
        assert metrics["operating_cost"]["label"] == "Screening_Estimate"
        assert metrics["operating_cost"]["amount"] is not None
        assert metrics["outage_service"]["label"] == "Outage_Service_Screening"
        assert metrics["outage_service"]["status"] == "evaluated"
        assert metrics["outage_service"]["critical_unserved_energy"] is not None
        assert metrics["outage_service"]["interruption_duration"] is not None
        assert (
            metrics["purchased_electricity_emissions"]["name"]
            == "Purchased_Electricity_Emissions_Estimate"
        )
        assert metrics["purchased_electricity_emissions"]["estimate"] is not None
        assert metrics["clean_energy_share"]["share"] is not None
        assert metrics["peak_import"] is not None
        assert metrics["critical_service_fraction"] is not None

    for label in (
        "Fast_Judge_MVP",
        "Screening_Estimate",
        "Outage_Service_Screening",
        EXPECTED_REPORT_FINGERPRINT,
    ):
        assert label.encode() in html.body
    assert upload.status == 404
    assert customer_data.status == forecasts.status == 404


PUBLIC_ENVIRONMENT = {
    "HOST": "0.0.0.0",
    "PORT": "10000",
    "WEB_CONCURRENCY": "1",
    "OMNIGRIDX_DATASET_IDS": sample_module.SAMPLE_DATASET_ID,
    "SERVICE_API_TOKEN": "must-not-appear-in-any-response",
}
DEFERRED_PATHS = (
    "/upload",
    "/api/sources",
    "/api/remote-adapters",
    "/api/customer-data",
    "/api/commercial-validation",
    "/api/auth",
    "/api/policy",
    "/api/state-packs",
    "/api/tariffs",
    "/api/forecasts",
    "/docs",
)
DISALLOWED_METHODS = (
    ("/healthz", "POST"),
    ("/", "POST"),
    ("/api/sample-report", "POST"),
    ("/api/sample-run", "GET"),
)


def test_demo_public_restarts_from_fresh_state_and_denies_other_routes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundled_bytes = (
        files("omnigridx.infrastructure")
        .joinpath("data/sample/judge-scenario-v1.json")
        .read_bytes()
    )

    async def boot(state_directory: Path) -> list[AsgiResponse]:
        snapshots = LocalSnapshotRepository(state_directory)
        snapshot = snapshots.put_once(bundled_bytes, "application/json")
        monkeypatch.setattr(
            sample_module, "_sample_bytes", lambda: snapshots.get_verified(snapshot)
        )
        app = create_app(mode="demo-public", environment=PUBLIC_ENVIRONMENT)
        assert not app.state.runtime.ready
        assert [getattr(route, "path") for route in app.routes] == [
            "/healthz",
            "/",
            "/api/sample-report",
            "/api/sample-run",
            "/assets",
        ]
        responses = [await _request(app, "/healthz")]
        async with app.router.lifespan_context(app):
            assert app.state.runtime.ready
            responses.extend(
                [
                    await _request(app, "/healthz"),
                    await _request(app, "/"),
                    await _request(app, "/api/sample-report"),
                    await _request(app, "/api/sample-run", "POST"),
                ]
            )
            responses.extend([await _request(app, path) for path in DEFERRED_PATHS])
            responses.extend(
                [
                    await _request(app, path, method)
                    for path, method in DISALLOWED_METHODS
                ]
            )
        assert not app.state.runtime.ready
        assert snapshots.get_verified(snapshot) == bundled_bytes
        return responses

    first = asyncio.run(boot(tmp_path / "first-boot"))
    second = asyncio.run(boot(tmp_path / "second-boot"))

    for responses in (first, second):
        initializing, health, page, report, rerun = responses[:5]
        assert initializing.status == 503
        assert initializing.json() == {"status": "initializing"}
        assert health.status == page.status == report.status == rerun.status == 200
        assert health.json()["status"] == "ready"
        assert health.json()["mode"] == "demo-public"
        assert {
            health.json()["report_fingerprint"],
            report.json()["report_fingerprint"],
            rerun.json()["report_fingerprint"],
        } == {report.json()["report_fingerprint"]}
        denied = responses[5 : 5 + len(DEFERRED_PATHS)]
        wrong_methods = responses[5 + len(DEFERRED_PATHS) :]
        assert all(response.status == 404 for response in denied)
        assert all(response.status == 405 for response in wrong_methods)
        assert all(
            PUBLIC_ENVIRONMENT["SERVICE_API_TOKEN"].encode() not in response.body
            for response in responses
        )

    assert (
        first[3].json()["report_fingerprint"]
        == second[3].json()["report_fingerprint"]
    )


def test_demo_local_rejects_non_loopback_binding() -> None:
    with pytest.raises(RuntimeError, match="loopback"):
        create_app(
            mode="demo-local",
            environment={"HOST": "0.0.0.0", "PORT": "8000"},
        )
