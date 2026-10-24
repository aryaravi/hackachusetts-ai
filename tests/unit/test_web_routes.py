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
            "headers": (),
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


def test_sample_routes_serve_one_initialized_report() -> None:
    async def requests(app: Starlette) -> tuple[AsgiResponse, ...]:
        return (
            await _request(app, "/healthz"),
            await _request(app, "/"),
            await _request(app, "/api/sample-report"),
            await _request(app, "/api/sample-run", method="POST"),
        )

    health, page, report, rerun = _run(requests)
    document = report.json()

    assert health.status == page.status == report.status == rerun.status == 200
    assert health.json() == {
        "status": "ready",
        "mode": "demo-local",
        "sample_id": document["sample_id"],
        "report_fingerprint": document["report_fingerprint"],
    }
    assert page.headers[b"content-type"].startswith(b"text/html")
    assert b"OmniGridX | Fast Judge MVP" in page.body
    assert [item["alternative"] for item in document["alternatives"]] == [
        "existing",
        "rule_based",
        "optimized",
    ]
    assert rerun.json() == document


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
            await _request(app, "/upload", method="POST", body=b"customer data"),
            await _request(app, "/api/customer-data"),
        )

    supplied_data, unsupported_method, upload, customer_route = _run(requests)

    assert supplied_data.status == 400
    assert supplied_data.json() == {"error": "caller-supplied data is not accepted"}
    assert unsupported_method.status == 405
    assert upload.status == customer_route.status == 404


def test_health_and_report_are_unavailable_before_initialization() -> None:
    async def requests() -> tuple[AsgiResponse, AsgiResponse]:
        app = create_app(environment={"HOST": "127.0.0.1", "PORT": "8000"})
        return (
            await _request(app, "/healthz"),
            await _request(app, "/api/sample-report"),
        )

    health, report = asyncio.run(requests())

    assert health.status == report.status == 503
    assert health.json() == report.json() == {"status": "initializing"}
