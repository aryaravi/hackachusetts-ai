"""Bounded, payload-free validator for a deployed judge demo."""

import argparse
import json
import time
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_DENIED_PATHS = ("/api/upload", "/api/policy", "/api/customer-data", "/admin")
_MAX_ATTEMPTS = 10
_MAX_TIMEOUT_SECONDS = 30
_MAX_RETRY_DELAY_SECONDS = 30
_REQUEST_ERRORS = (TimeoutError, URLError, json.JSONDecodeError)


def _request(base_url: str, path: str, timeout: float) -> tuple[int, dict[str, Any]]:
    request = Request(
        base_url.rstrip("/") + path,
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - HTTPS is enforced below
            body = response.read()
            return response.status, cast(dict[str, Any], json.loads(body)) if body else {}
    except HTTPError as error:
        return error.code, {}


def validate_hosted_demo(
    base_url: str,
    expected_fingerprint: str,
    *,
    attempts: int = 4,
    timeout_seconds: float = 8,
    retry_delay_seconds: float = 2,
) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("hosted demo URL must be public HTTPS without credentials")
    if not 1 <= attempts <= _MAX_ATTEMPTS:
        raise ValueError(f"attempts must be between 1 and {_MAX_ATTEMPTS}")
    if not 0 < timeout_seconds <= _MAX_TIMEOUT_SECONDS:
        raise ValueError(f"timeout must be between 0 and {_MAX_TIMEOUT_SECONDS} seconds")
    if not 0 <= retry_delay_seconds <= _MAX_RETRY_DELAY_SECONDS:
        raise ValueError(
            f"retry delay must be between 0 and {_MAX_RETRY_DELAY_SECONDS} seconds"
        )

    last_error = "health check did not become ready"
    for attempt in range(attempts):
        try:
            status, health = _request(base_url, "/healthz", timeout_seconds)
            if status == 200 and health.get("status") == "ready":
                break
            last_error = f"health check returned {status}"
        except _REQUEST_ERRORS as error:
            detail = str(error) or type(error).__name__
            last_error = f"health check failed: {detail}"
        if attempt + 1 < attempts:
            time.sleep(retry_delay_seconds)
    else:
        raise RuntimeError(last_error)

    try:
        status, report = _request(base_url, "/api/sample-report", timeout_seconds)
    except _REQUEST_ERRORS as error:
        raise RuntimeError("sample report request failed") from error
    if status != 200:
        raise RuntimeError(f"sample report returned {status}")
    if report.get("report_fingerprint") != expected_fingerprint:
        raise RuntimeError("sample report fingerprint mismatch")
    for path in _DENIED_PATHS:
        try:
            denied_status, _ = _request(base_url, path, timeout_seconds)
        except _REQUEST_ERRORS as error:
            raise RuntimeError(f"restricted route check failed: {path}") from error
        if denied_status not in {404, 405}:
            raise RuntimeError(f"restricted route is unexpectedly available: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("expected_fingerprint")
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=8)
    args = parser.parse_args()
    validate_hosted_demo(
        args.base_url,
        args.expected_fingerprint,
        attempts=args.attempts,
        timeout_seconds=args.timeout,
    )
    print("Hosted judge demo is ready and fail-closed.")


if __name__ == "__main__":
    main()
