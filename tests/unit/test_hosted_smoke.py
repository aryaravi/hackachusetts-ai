from collections.abc import Iterator
import time
from typing import Any

import pytest

from omnigridx.web import smoke


BASE_URL = "https://demo.example"
FINGERPRINT = "a" * 64


def responses(*values: tuple[int, dict[str, Any]]) -> Iterator[tuple[int, dict[str, Any]]]:
    return iter(values)


def test_hosted_smoke_checks_health_report_and_restricted_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = responses(
        (200, {"status": "ready"}),
        (200, {"report_fingerprint": FINGERPRINT}),
        *((404, {}) for _ in smoke._DENIED_PATHS),
    )
    calls: list[tuple[str, str, float]] = []

    def request(base_url: str, path: str, timeout: float) -> tuple[int, dict[str, Any]]:
        calls.append((base_url, path, timeout))
        return next(values)

    monkeypatch.setattr(smoke, "_request", request)
    smoke.validate_hosted_demo(BASE_URL, FINGERPRINT, timeout_seconds=3)

    assert calls == [
        (BASE_URL, path, 3)
        for path in ("/healthz", "/api/sample-report", *smoke._DENIED_PATHS)
    ]


def test_hosted_smoke_retries_a_cold_start(monkeypatch: pytest.MonkeyPatch) -> None:
    values = responses(
        (503, {"status": "initializing"}),
        (200, {"status": "ready"}),
        (200, {"report_fingerprint": FINGERPRINT}),
        *((405, {}) for _ in smoke._DENIED_PATHS),
    )
    paths: list[str] = []
    sleeps: list[float] = []

    def request(_: str, path: str, __: float) -> tuple[int, dict[str, Any]]:
        paths.append(path)
        return next(values)

    monkeypatch.setattr(smoke, "_request", request)
    monkeypatch.setattr(time, "sleep", sleeps.append)

    smoke.validate_hosted_demo(
        BASE_URL,
        FINGERPRINT,
        attempts=2,
        timeout_seconds=1,
        retry_delay_seconds=0.25,
    )

    assert paths[:2] == ["/healthz", "/healthz"]
    assert sleeps == [0.25]


def test_hosted_smoke_rejects_report_fingerprint_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = responses(
        (200, {"status": "ready"}),
        (200, {"report_fingerprint": "b" * 64}),
    )
    monkeypatch.setattr(smoke, "_request", lambda *_: next(values))

    with pytest.raises(RuntimeError, match="fingerprint mismatch"):
        smoke.validate_hosted_demo(BASE_URL, FINGERPRINT)


def test_hosted_smoke_rejects_non_https_url(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_request(*_: object) -> tuple[int, dict[str, Any]]:
        raise AssertionError("non-HTTPS URL triggered a request")

    monkeypatch.setattr(smoke, "_request", unexpected_request)

    with pytest.raises(ValueError, match="public HTTPS"):
        smoke.validate_hosted_demo("http://demo.example", FINGERPRINT)


def test_hosted_smoke_stops_after_bounded_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def timeout(*_: object) -> tuple[int, dict[str, Any]]:
        nonlocal calls
        calls += 1
        raise TimeoutError

    monkeypatch.setattr(smoke, "_request", timeout)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="TimeoutError"):
        smoke.validate_hosted_demo(
            BASE_URL,
            FINGERPRINT,
            attempts=3,
            timeout_seconds=0.5,
            retry_delay_seconds=0,
        )

    assert calls == 3


def test_hosted_smoke_rejects_unexpectedly_open_restricted_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def request(_: str, path: str, __: float) -> tuple[int, dict[str, Any]]:
        if path == "/healthz":
            return 200, {"status": "ready"}
        if path == "/api/sample-report":
            return 200, {"report_fingerprint": FINGERPRINT}
        return (200 if path == smoke._DENIED_PATHS[0] else 404), {}

    monkeypatch.setattr(smoke, "_request", request)

    with pytest.raises(RuntimeError, match=smoke._DENIED_PATHS[0]):
        smoke.validate_hosted_demo(BASE_URL, FINGERPRINT)
