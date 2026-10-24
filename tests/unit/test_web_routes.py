import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import json
from typing import Any, cast

from starlette.applications import Starlette
from starlette.types import Message

from omnigridx.web.app import create_app


@dataclass(frozen=True)
class AsgiResponse:
    status: int
    headers: dict[bytes, bytes]
    body: bytes

    def json(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.body))


async def _request(
    app: Starlette,
    path: str,
    *,
    method: str = "GET",
    body: bytes = b"",
    headers: tuple[tuple[bytes, bytes], ...] = (),
) -> AsgiResponse:
    sent: list[Message] = []
    received = False

    async def receive() -> Message:
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

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
            "headers": headers,
            "client": ("127.0.0.1", 50000),
            "server": ("127.0.0.1", 8000),
        },
        receive,
        send,
    )
    start = next(message for message in sent if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    return AsgiResponse(start["status"], dict(start["headers"]), response_body)


def _run(
    operation: Callable[[Starlette], Awaitable[tuple[AsgiResponse, ...]]],
) -> tuple[AsgiResponse, ...]:
    async def run_requests() -> tuple[AsgiResponse, ...]:
        app = create_app(environment={"HOST": "127.0.0.1", "PORT": "8000"})
        async with app.router.lifespan_context(app):
            return await operation(app)

    return asyncio.run(run_requests())


def test_full_stack_pages_serve_one_unchanged_checked_report() -> None:
    page_paths = (
        "/",
        "/overview",
        "/grid-data",
        "/clean-options",
        "/ai-draft",
        "/approvals",
        "/sources",
    )

    async def requests(app: Starlette) -> tuple[AsgiResponse, ...]:
        pages = tuple([await _request(app, path) for path in page_paths])
        return (
            await _request(app, "/healthz"),
            *pages,
            await _request(app, "/api/sample-report"),
            await _request(app, "/api/sample-run", method="POST"),
            await _request(app, "/api/simulation"),
        )

    responses = _run(requests)
    health = responses[0]
    pages = responses[1 : 1 + len(page_paths)]
    report, rerun, simulation = responses[-3:]
    document = report.json()

    assert health.status == report.status == rerun.status == simulation.status == 200
    assert all(page.status == 200 for page in pages)
    assert all(page.headers[b"content-type"].startswith(b"text/html") for page in pages)
    assert all(b"OmniGridX | Grid Intelligence Demo" in page.body for page in pages)
    assert health.json() == {
        "status": "ready",
        "mode": "demo-local",
        "sample_id": document["sample_id"],
        "report_fingerprint": document["report_fingerprint"],
    }
    assert [item["alternative"] for item in document["alternatives"]] == [
        "existing",
        "rule_based",
        "optimized",
    ]
    assert rerun.json() == document
    assert simulation.json()["report_fingerprint"] == document["report_fingerprint"]
    assert simulation.json()["mode"] == "simulated"
    assert simulation.headers[b"cache-control"] == b"no-store"


def test_simulated_approval_api_enforces_input_and_role_order() -> None:
    json_headers = ((b"content-type", b"application/json"),)

    async def requests(app: Starlette) -> tuple[AsgiResponse, ...]:
        responses = [
            await _request(
                app,
                "/api/simulation/approvals",
                method="POST",
                body=b'{"role":"manager"}',
                headers=json_headers,
            ),
            await _request(
                app,
                "/api/simulation/approvals",
                method="POST",
                body=b'{"role":"unknown"}',
                headers=json_headers,
            ),
            await _request(
                app,
                "/api/simulation/approvals",
                method="POST",
                body=b'{"role":"analyst","comment":"not accepted"}',
                headers=json_headers,
            ),
            await _request(
                app,
                "/api/simulation/approvals",
                method="POST",
                body=b'{"role":"analyst"}',
            ),
            await _request(
                app,
                "/api/simulation/approvals",
                method="POST",
                body=b"x" * 257,
                headers=json_headers,
            ),
        ]
        for role in (
            "analyst",
            "energy_provider_representative",
            "government_reviewer",
            "manager",
        ):
            responses.append(
                await _request(
                    app,
                    "/api/simulation/approvals",
                    method="POST",
                    body=json.dumps({"role": role}).encode(),
                    headers=json_headers,
                )
            )
        responses.append(
            await _request(app, "/api/simulation/reset", method="POST")
        )
        return tuple(responses)

    skipped, unknown, extra, wrong_type, too_large, *transitions, reset = _run(requests)

    assert skipped.status == 409
    assert unknown.status == extra.status == 400
    assert wrong_type.status == 415
    assert too_large.status == 413
    assert [response.json()["approval_flow"]["progress"] for response in transitions] == [
        "1/4",
        "2/4",
        "3/4",
        "4/4",
    ]
    assert transitions[-1].json()["approval_flow"]["status"] == "simulated_authorization_complete"
    assert reset.status == 200
    assert reset.json()["approval_flow"]["next_role"] == "analyst"


def test_routes_reject_caller_data_uploads_and_unsupported_methods() -> None:
    async def requests(app: Starlette) -> tuple[AsgiResponse, ...]:
        return (
            await _request(
                app,
                "/api/sample-run",
                method="POST",
                body=b'{"scenario":"caller supplied"}',
            ),
            await _request(app, "/api/sample-report", method="POST"),
            await _request(app, "/api/simulation", method="POST"),
            await _request(app, "/upload", method="POST", body=b"customer data"),
            await _request(app, "/api/customer-data"),
        )

    supplied_data, report_method, simulation_method, upload, customer_route = _run(requests)

    assert supplied_data.status == 400
    assert supplied_data.json() == {"error": "caller-supplied data is not accepted"}
    assert report_method.status == simulation_method.status == 405
    assert upload.status == customer_route.status == 404


def test_health_and_reports_are_unavailable_before_initialization() -> None:
    async def requests() -> tuple[AsgiResponse, AsgiResponse, AsgiResponse]:
        app = create_app(environment={"HOST": "127.0.0.1", "PORT": "8000"})
        return (
            await _request(app, "/healthz"),
            await _request(app, "/api/sample-report"),
            await _request(app, "/api/simulation"),
        )

    health, report, simulation = asyncio.run(requests())

    assert health.status == report.status == simulation.status == 503
    assert health.json() == report.json() == simulation.json() == {"status": "initializing"}
