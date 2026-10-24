"""Fail-closed Starlette host for the checked report and hackathon simulation."""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from omnigridx.application.capability_gate import (
    CapabilityGate,
    DemoLocalSettings,
    DemoPublicSettings,
)
from omnigridx.application.reporting import JudgeReport
from omnigridx.infrastructure.hackathon import (
    ApprovalConflict,
    ApprovalFlow,
    build_simulated_ai_draft,
    load_official_data,
)
from omnigridx.infrastructure.sample import SAMPLE_DATASET_ID, build_sample_report

_MAX_APPROVAL_BODY_BYTES = 256
_PAGE_PATHS = ("/", "/overview", "/grid-data", "/clean-options", "/ai-draft", "/approvals", "/sources")


@dataclass(slots=True)
class RuntimeState:
    mode: str
    report: JudgeReport | None = None
    official_data: dict[str, Any] | None = None
    official_snapshot_fingerprint: str | None = None
    ai_draft: dict[str, Any] | None = None
    approvals: ApprovalFlow | None = None

    @property
    def ready(self) -> bool:
        return all(
            value is not None
            for value in (
                self.report,
                self.official_data,
                self.official_snapshot_fingerprint,
                self.ai_draft,
                self.approvals,
            )
        )


def _enabled(environment: Mapping[str, str], name: str) -> bool:
    return environment.get(name, "").strip().lower() not in {
        "",
        "0",
        "false",
        "no",
        "off",
    }


def _integer(
    environment: Mapping[str, str], name: str, default: str | None = None
) -> int:
    value = environment.get(name, default)
    if value is None:
        raise RuntimeError(f"{name} is required")
    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error


def _validate_startup(mode: str, environment: Mapping[str, str]) -> tuple[str, int]:
    gate = CapabilityGate(frozenset({SAMPLE_DATASET_ID}))
    restricted = {
        "uploads_enabled": _enabled(environment, "OMNIGRIDX_ENABLE_UPLOADS"),
        "remote_adapters_enabled": _enabled(
            environment, "OMNIGRIDX_ENABLE_REMOTE_ADAPTERS"
        ),
        "customer_data_enabled": _enabled(
            environment, "OMNIGRIDX_ENABLE_CUSTOMER_DATA"
        ),
    }
    if mode == "demo-local":
        host = environment.get("HOST", "127.0.0.1")
        port = _integer(environment, "PORT", "8000")
        decision = gate.validate_demo_local_startup(
            DemoLocalSettings(host, (SAMPLE_DATASET_ID,), **restricted)
        )
    elif mode == "demo-public":
        host = environment.get("HOST", "0.0.0.0")
        port = _integer(environment, "PORT")
        dataset_ids = tuple(
            dataset_id.strip()
            for dataset_id in environment.get(
                "OMNIGRIDX_DATASET_IDS", SAMPLE_DATASET_ID
            ).split(",")
            if dataset_id.strip()
        )
        decision = gate.validate_demo_public_startup(
            DemoPublicSettings(
                bind_host=host,
                port=port,
                dataset_ids=dataset_ids,
                uploads_enabled=restricted["uploads_enabled"],
                arbitrary_sources_enabled=_enabled(
                    environment, "OMNIGRIDX_ENABLE_SOURCE_REGISTRATION"
                ),
                remote_adapters_enabled=restricted["remote_adapters_enabled"],
                customer_data_enabled=restricted["customer_data_enabled"],
                deferred_operations_enabled=any(
                    _enabled(environment, name)
                    for name in (
                        "OMNIGRIDX_ENABLE_AUTHENTICATION",
                        "OMNIGRIDX_ENABLE_COMMERCIAL",
                        "OMNIGRIDX_ENABLE_POLICY",
                        "OMNIGRIDX_ENABLE_STATE_ADMIN",
                        "OMNIGRIDX_ENABLE_TARIFFS",
                        "OMNIGRIDX_ENABLE_FORECASTS",
                    )
                ),
                deferred_runtime_imports_enabled=_enabled(
                    environment, "OMNIGRIDX_ENABLE_DEFERRED_IMPORTS"
                ),
                workers=_integer(environment, "WEB_CONCURRENCY", "1"),
                persistent_storage_enabled=_enabled(
                    environment, "OMNIGRIDX_ENABLE_PERSISTENCE"
                ),
                response_visible_secret_names=tuple(
                    value.strip()
                    for value in environment.get(
                        "OMNIGRIDX_RESPONSE_SECRETS", ""
                    ).split(",")
                    if value.strip()
                ),
            )
        )
    else:
        raise RuntimeError("OMNIGRIDX_MODE must be demo-local or demo-public")
    if not decision.allowed:
        raise RuntimeError(
            "unsafe startup configuration: " + "; ".join(decision.reasons)
        )
    return host, port


def create_app(
    mode: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> Starlette:
    selected_environment = os.environ if environment is None else environment
    selected_mode: str = (
        mode or selected_environment.get("OMNIGRIDX_MODE") or "demo-local"
    )
    _validate_startup(selected_mode, selected_environment)
    runtime = RuntimeState(selected_mode)
    static_dir = Path(__file__).with_name("static")
    index_path = static_dir / "index.html"

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        runtime.report = build_sample_report(selected_mode)
        (
            runtime.official_data,
            runtime.official_snapshot_fingerprint,
        ) = load_official_data()
        runtime.ai_draft = build_simulated_ai_draft(
            runtime.report,
            runtime.official_data,
            runtime.official_snapshot_fingerprint,
        )
        runtime.approvals = ApprovalFlow()
        yield
        runtime.report = None
        runtime.official_data = None
        runtime.official_snapshot_fingerprint = None
        runtime.ai_draft = None
        runtime.approvals = None

    def unavailable() -> JSONResponse:
        return JSONResponse({"status": "initializing"}, status_code=503)

    def simulation_payload() -> dict[str, Any] | None:
        if not runtime.ready:
            return None
        assert runtime.report is not None
        assert runtime.official_data is not None
        assert runtime.official_snapshot_fingerprint is not None
        assert runtime.ai_draft is not None
        assert runtime.approvals is not None
        return {
            "schema_version": "hackathon-simulation/1.0",
            "mode": "simulated",
            "disclosure": "Public-data, AI-report, identity, financial, operational, and approval behavior on these pages is a hackathon simulation only.",
            "report_fingerprint": runtime.report.fingerprint,
            "official_snapshot_fingerprint": runtime.official_snapshot_fingerprint,
            "official_data": runtime.official_data,
            "ai_draft": runtime.ai_draft,
            "approval_flow": runtime.approvals.to_dict(),
        }

    async def health(_: Request) -> JSONResponse:
        if not runtime.ready:
            return unavailable()
        assert runtime.report is not None
        return JSONResponse(
            {
                "status": "ready",
                "mode": runtime.mode,
                "sample_id": runtime.report.sample_id,
                "report_fingerprint": runtime.report.fingerprint,
            }
        )

    async def index(_: Request) -> Response:
        if not runtime.ready:
            return unavailable()
        return HTMLResponse(index_path.read_text(encoding="utf-8"))

    async def sample_report(_: Request) -> Response:
        if runtime.report is None:
            return unavailable()
        return Response(runtime.report.to_json(), media_type="application/json")

    async def sample_run(request: Request) -> Response:
        if await request.body():
            return JSONResponse(
                {"error": "caller-supplied data is not accepted"}, status_code=400
            )
        runtime.report = build_sample_report(selected_mode)
        if runtime.official_data is not None and runtime.official_snapshot_fingerprint is not None:
            runtime.ai_draft = build_simulated_ai_draft(
                runtime.report,
                runtime.official_data,
                runtime.official_snapshot_fingerprint,
            )
        return Response(runtime.report.to_json(), media_type="application/json")

    async def simulation(_: Request) -> JSONResponse:
        payload = simulation_payload()
        return unavailable() if payload is None else JSONResponse(payload, headers={"Cache-Control": "no-store"})

    async def approve(request: Request) -> JSONResponse:
        payload = simulation_payload()
        if payload is None:
            return unavailable()
        content_length = request.headers.get("content-length")
        try:
            if content_length is not None and int(content_length) > _MAX_APPROVAL_BODY_BYTES:
                return JSONResponse({"error": "approval request is too large"}, status_code=413)
        except ValueError:
            return JSONResponse({"error": "invalid content length"}, status_code=400)
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            return JSONResponse({"error": "application/json is required"}, status_code=415)
        body = await request.body()
        if len(body) > _MAX_APPROVAL_BODY_BYTES:
            return JSONResponse({"error": "approval request is too large"}, status_code=413)
        try:
            document = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JSONResponse({"error": "invalid approval request"}, status_code=400)
        if not isinstance(document, dict) or set(document) != {"role"} or not isinstance(document["role"], str):
            return JSONResponse({"error": "approval request requires only a role"}, status_code=400)
        assert runtime.approvals is not None
        try:
            runtime.approvals.approve(document["role"])
        except ApprovalConflict as error:
            return JSONResponse({"error": str(error)}, status_code=409)
        except ValueError as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        updated = simulation_payload()
        assert updated is not None
        return JSONResponse(updated, headers={"Cache-Control": "no-store"})

    async def reset_simulation(request: Request) -> JSONResponse:
        if not runtime.ready:
            return unavailable()
        if await request.body():
            return JSONResponse({"error": "reset does not accept a body"}, status_code=400)
        assert runtime.approvals is not None
        runtime.approvals.reset()
        updated = simulation_payload()
        assert updated is not None
        return JSONResponse(updated, headers={"Cache-Control": "no-store"})

    routes = [
        Route("/healthz", health, methods=["GET"]),
        *(Route(path, index, methods=["GET"]) for path in _PAGE_PATHS),
        Route("/api/sample-report", sample_report, methods=["GET"]),
        Route("/api/sample-run", sample_run, methods=["POST"]),
        Route("/api/simulation", simulation, methods=["GET"]),
        Route("/api/simulation/approvals", approve, methods=["POST"]),
        Route("/api/simulation/reset", reset_simulation, methods=["POST"]),
        Mount(
            "/assets",
            StaticFiles(directory=static_dir / "assets", check_dir=False),
            name="assets",
        ),
    ]
    app = Starlette(routes=routes, lifespan=lifespan)
    app.state.runtime = runtime
    return app


app = create_app()
