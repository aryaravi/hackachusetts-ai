from pathlib import Path

import pytest
from starlette.routing import Mount, Route

from omnigridx.infrastructure.sample import SAMPLE_DATASET_ID
from omnigridx.web.app import RuntimeState, create_app


SAFE_PUBLIC_ENVIRONMENT = {
    "HOST": "0.0.0.0",
    "PORT": "10000",
    "WEB_CONCURRENCY": "1",
    "OMNIGRIDX_DATASET_IDS": SAMPLE_DATASET_ID,
}


def test_demo_public_accepts_only_ephemeral_sample_configuration() -> None:
    app = create_app(mode="demo-public", environment=SAFE_PUBLIC_ENVIRONMENT)
    runtime: RuntimeState = app.state.runtime

    assert runtime.mode == "demo-public"
    assert not runtime.ready
    assert [
        route.path
        for route in app.routes
        if isinstance(route, (Route, Mount))
    ] == [
        "/healthz",
        "/",
        "/api/sample-report",
        "/api/sample-run",
        "/assets",
    ]


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"HOST": "127.0.0.1"}, "platform bind host"),
        ({"PORT": "not-a-port"}, "PORT must be an integer"),
        ({"PORT": "0"}, "valid platform port"),
        ({"OMNIGRIDX_DATASET_IDS": ""}, "bundled sample dataset"),
        ({"OMNIGRIDX_DATASET_IDS": "customer-data"}, "not bundled samples"),
        ({"OMNIGRIDX_ENABLE_UPLOADS": "1"}, "uploads"),
        ({"OMNIGRIDX_ENABLE_SOURCE_REGISTRATION": "1"}, "source registration"),
        ({"OMNIGRIDX_ENABLE_REMOTE_ADAPTERS": "1"}, "remote adapters"),
        ({"OMNIGRIDX_ENABLE_CUSTOMER_DATA": "1"}, "customer data"),
        ({"OMNIGRIDX_ENABLE_AUTHENTICATION": "1"}, "deferred operations"),
        ({"OMNIGRIDX_ENABLE_COMMERCIAL": "1"}, "deferred operations"),
        ({"OMNIGRIDX_ENABLE_POLICY": "1"}, "deferred operations"),
        ({"OMNIGRIDX_ENABLE_STATE_ADMIN": "1"}, "deferred operations"),
        ({"OMNIGRIDX_ENABLE_TARIFFS": "1"}, "deferred operations"),
        ({"OMNIGRIDX_ENABLE_FORECASTS": "1"}, "deferred operations"),
        ({"OMNIGRIDX_ENABLE_DEFERRED_IMPORTS": "1"}, "runtime imports"),
        ({"WEB_CONCURRENCY": "2"}, "exactly one in-memory worker"),
        ({"OMNIGRIDX_ENABLE_PERSISTENCE": "1"}, "persistent storage"),
        ({"OMNIGRIDX_RESPONSE_SECRETS": "API_TOKEN"}, "secrets"),
    ],
)
def test_demo_public_fails_closed_for_unsafe_configuration(
    override: dict[str, str], reason: str
) -> None:
    environment = {**SAFE_PUBLIC_ENVIRONMENT, **override}

    with pytest.raises(RuntimeError, match=reason):
        create_app(mode="demo-public", environment=environment)


def test_render_blueprint_is_one_free_python_web_service() -> None:
    blueprint = (Path(__file__).parents[2] / "render.yaml").read_text(
        encoding="utf-8"
    )

    assert blueprint.count("  - type:") == 1
    for required in (
        "type: web",
        "runtime: python",
        "plan: free",
        "PYTHON_VERSION",
        "value: 3.13.13",
        "OMNIGRIDX_MODE",
        "value: demo-public",
        "healthCheckPath: /healthz",
        "python -m uvicorn omnigridx.web.app:app --host 0.0.0.0 --port $PORT --workers 1",
    ):
        assert required in blueprint
    for forbidden in (
        "type: worker",
        "runtime: docker",
        "databases:",
        "disk:",
        "authToken:",
    ):
        assert forbidden not in blueprint
