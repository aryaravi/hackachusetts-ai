"""Sample-only Starlette API and report host."""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
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
from omnigridx.infrastructure.sample import SAMPLE_DATASET_ID, build_sample_report
from omnigridx.web.presentation import ReportPresenter


@dataclass(slots=True)
class RuntimeState:
    mode: str
    report: JudgeReport | None = None

    @property
    def ready(self) -> bool:
        return self.report is not None


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
    presenter = ReportPresenter()

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        runtime.report = build_sample_report(selected_mode)
        yield
        runtime.report = None

    def report_or_unavailable() -> JudgeReport | JSONResponse:
        if runtime.report is None:
            return JSONResponse({"status": "initializing"}, status_code=503)
        return runtime.report

    async def health(_: Request) -> JSONResponse:
        report = runtime.report
        if report is None:
            return JSONResponse({"status": "initializing"}, status_code=503)
        return JSONResponse(
            {
                "status": "ready",
                "mode": runtime.mode,
                "sample_id": report.sample_id,
                "report_fingerprint": report.fingerprint,
            }
        )

    async def index(_: Request) -> Response:
        report = report_or_unavailable()
        return (
            report
            if isinstance(report, JSONResponse)
            else HTMLResponse(presenter.render_html(report))
        )

    async def sample_report(_: Request) -> Response:
        report = report_or_unavailable()
        return (
            report
            if isinstance(report, JSONResponse)
            else Response(presenter.render_json(report), media_type="application/json")
        )

    async def sample_run(request: Request) -> JSONResponse | Response:
        if await request.body():
            return JSONResponse(
                {"error": "caller-supplied data is not accepted"}, status_code=400
            )
        runtime.report = build_sample_report(selected_mode)
        return Response(
            presenter.render_json(runtime.report), media_type="application/json"
        )

    static_dir = Path(__file__).with_name("static")
    routes = [
        Route("/healthz", health, methods=["GET"]),
        Route("/", index, methods=["GET"]),
        Route("/api/sample-report", sample_report, methods=["GET"]),
        Route("/api/sample-run", sample_run, methods=["POST"]),
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
