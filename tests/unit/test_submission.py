"""Submission package validation fixtures."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
from typing import Any, cast

import pytest

from omnigridx.infrastructure.sample import build_sample_report
from omnigridx.submission import validate_submission


_REQUIRED_FILES = (
    "LICENSE",
    "README.md",
    "SUBMISSION_WRITEUP.md",
    "render.yaml",
    "src/omnigridx/infrastructure/data/sample/judge-scenario-v1.json",
    ".kiro/specs/omnigridx/.config.kiro",
    ".kiro/specs/omnigridx/requirements.md",
    ".kiro/specs/omnigridx/design.md",
    ".kiro/specs/omnigridx/tasks.md",
    ".kiro/specs/omnigridx/tasks.meta.json",
    ".kiro/hooks/task-checks.json",
    ".kiro/hooks/task_validation.py",
    ".kiro/steering/task-validation.md",
)
_REQUIRED_NOTICES = (
    "React",
    "Vite",
    "Starlette",
    "Uvicorn",
    "Jinja2",
    "SciPy",
    "NumPy",
    "setuptools",
    "build",
    "pytest",
    "Hypothesis",
    "mypy",
    "src/omnigridx/web/static/assets/app.js",
    "judge-scenario-v1.json",
    "LICENSE",
)


def _metadata(*, draft: bool = True) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "status": "draft" if draft else "submitted",
        "track": "Climate Tech & Clean Energy",
        "project_name": "OmniGridX",
        "project_description": "Bundled sample judge demo.",
        "repository_url": "https://github.com/example/omnigridx",
        "public_demo": {
            "provider": "Render",
            "base_url": "REPLACE_WITH_RENDER_HTTPS_URL" if draft else "https://omnigridx-judge-demo.onrender.com",
            "health_path": "/healthz",
            "report_path": "/api/sample-report",
            "report_fingerprint": "REPLACE_AFTER_PUBLIC_MODE_RUN" if draft else build_sample_report("demo-public").fingerprint,
        },
        "local_judge": {
            "command": "make demo",
            "test_command": "make check",
            "url": "http://127.0.0.1:8000",
            "requires_login": False,
            "accepts_user_data": False,
        },
        "data_policy": {
            "input_scope": "bundled synthetic non-customer sample only",
            "uploads_enabled": False,
            "remote_adapters_enabled": False,
            "contains_secrets": False,
            "contains_customer_data": False,
        },
        "hosting_disclosures": {
            "cold_start": "The free service may cold-start for several minutes.",
            "ephemeral_storage": "Storage is ephemeral; no persistence is claimed.",
            "free_tier_volatility": "Free-tier limits may change without notice.",
            "local_fallback": "Run make demo if hosted access is unavailable.",
        },
        "video": {
            "url": "REPLACE_WITH_PUBLIC_VIDEO_URL" if draft else "https://youtu.be/example",
            "duration_seconds": 0 if draft else 120,
            "approved_hosts": ["youtube.com", "youtu.be", "vimeo.com", "loom.com"],
        },
        "team_members": [] if draft else ["Example Member"],
        "authorized_representative": "REPLACE_WITH_TEAM_MEMBER" if draft else "Example Member",
        "representative_authorized": not draft,
        "kiro_evidence": [
            ".kiro/specs/omnigridx/requirements.md",
            ".kiro/specs/omnigridx/design.md",
            ".kiro/specs/omnigridx/tasks.md",
            ".kiro/hooks/task-checks.json",
            ".kiro/hooks/task_validation.py",
            ".kiro/steering/task-validation.md",
        ],
        "third_party_notices": "THIRD_PARTY_NOTICES.md",
        "artifact_license": "LICENSE",
        "final_submission_commit": "REPLACE_AT_SUBMISSION",
    }


def _write_fixture(root: Path, metadata: dict[str, Any]) -> None:
    readme = """python3.13 -m venv .venv
python -m pip install -e '.[dev]'
make demo
make check
Constrained grid intelligence; no AI, weather, or demand forecasting.
"""
    writeup = """Constrained grid intelligence with no AI, weather, or demand forecasting.
.kiro/specs/omnigridx/requirements.md
.kiro/hooks/task_validation.py
No quantitative workflow-effect measurement was collected.
"""
    for name in _REQUIRED_FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        content = readme if name == "README.md" else writeup if name == "SUBMISSION_WRITEUP.md" else "fixture"
        path.write_text(content, encoding="utf-8")
    (root / "THIRD_PARTY_NOTICES.md").write_text(
        "\n".join(_REQUIRED_NOTICES), encoding="utf-8"
    )
    (root / "submission-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    (root / ".gitignore").write_text(".venv/\n", encoding="utf-8")


def _run_git(root: Path, *args: str) -> str:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
    )
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _strict_fixture(root: Path) -> dict[str, Any]:
    metadata = _metadata(draft=False)
    _write_fixture(root, metadata)
    _run_git(root, "init", "--initial-branch=main")
    paths = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and ".git" not in path.parts]
    _run_git(root, "add", "--", *paths)
    _run_git(root, "commit", "-m", "fixture")
    metadata["final_submission_commit"] = _run_git(root, "rev-parse", "HEAD")
    (root / "submission-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def test_draft_fixture_accepts_human_owned_placeholders(tmp_path: Path) -> None:
    _write_fixture(tmp_path, _metadata())

    assert validate_submission(tmp_path, allow_draft=True) == ()


def test_strict_fixture_accepts_tracked_package_and_commit_field_only_change(tmp_path: Path) -> None:
    _strict_fixture(tmp_path)

    assert validate_submission(tmp_path) == ()


@pytest.mark.parametrize(
    ("path", "value", "expected_issue"),
    (
        (("public_demo", "provider"), "Other", "public demo provider must be Render"),
        (("public_demo", "base_url"), "http://demo.onrender.com", "public demo URL must be a Render HTTPS base URL or the draft placeholder"),
        (("public_demo", "base_url"), "REPLACE_SOMEDAY", "public demo URL must be a Render HTTPS base URL or the draft placeholder"),
        (("public_demo", "health_path"), "/health", "public health path must be /healthz"),
        (("public_demo", "report_path"), "/report", "public report path must be /api/sample-report"),
        (("public_demo", "report_fingerprint"), "a" * 64, "public report fingerprint must match the deterministic demo-public report"),
        (("local_judge", "command"), "python app.py", "local judge path must be unrestricted make demo on loopback with make check and no user data"),
        (("local_judge", "url"), "http://0.0.0.0:8000", "local judge path must be unrestricted make demo on loopback with make check and no user data"),
        (("data_policy", "contains_customer_data"), True, "submission data policy must exclude secrets and customer or remote input"),
        (("hosting_disclosures", "cold_start"), "May take time.", "invalid hosting disclosure: cold_start"),
        (("hosting_disclosures", "ephemeral_storage"), "Temporary storage.", "invalid hosting disclosure: ephemeral_storage"),
        (("hosting_disclosures", "free_tier_volatility"), "Availability varies.", "invalid hosting disclosure: free_tier_volatility"),
        (("hosting_disclosures", "local_fallback"), "Run locally.", "invalid hosting disclosure: local_fallback"),
    ),
)
def test_draft_fixtures_reject_invalid_paths_boundaries_and_disclosures(
    tmp_path: Path,
    path: tuple[str, str],
    value: object,
    expected_issue: str,
) -> None:
    metadata = deepcopy(_metadata())
    section = cast(dict[str, Any], metadata[path[0]])
    section[path[1]] = value
    _write_fixture(tmp_path, metadata)

    assert expected_issue in validate_submission(tmp_path, allow_draft=True)


def test_fixture_rejects_ignored_kiro_content(tmp_path: Path) -> None:
    _write_fixture(tmp_path, _metadata())
    (tmp_path / ".gitignore").write_text(".kiro/**\n", encoding="utf-8")

    assert ".kiro content must not be ignored" in validate_submission(tmp_path, allow_draft=True)


def test_fixture_rejects_secret_customer_data_and_executable(tmp_path: Path) -> None:
    _write_fixture(tmp_path, _metadata())
    (tmp_path / "config.txt").write_text("AKIA" + "A" * 16, encoding="utf-8")
    customer = tmp_path / "src" / "omnigridx" / "infrastructure" / "data" / "sample" / "customer.json"
    customer.write_text(json.dumps({"account_number": "synthetic"}), encoding="utf-8")
    (tmp_path / "unexpected.exe").write_bytes(b"fixture")

    issues = validate_submission(tmp_path, allow_draft=True)

    assert any("known secret pattern" in issue for issue in issues)
    assert any("customer-data fields" in issue for issue in issues)
    assert "undeclared executable artifact: unexpected.exe" in issues


def test_strict_fixture_rejects_untracked_required_file(tmp_path: Path) -> None:
    metadata = _strict_fixture(tmp_path)
    _run_git(tmp_path, "rm", "--cached", ".kiro/hooks/task_validation.py")
    (tmp_path / "submission-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    assert "required file is not tracked: .kiro/hooks/task_validation.py" in validate_submission(tmp_path)


def test_strict_fixture_rejects_changed_artifact_after_final_commit(tmp_path: Path) -> None:
    _strict_fixture(tmp_path)
    (tmp_path / "README.md").write_text(
        (tmp_path / "README.md").read_text(encoding="utf-8") + "changed\n",
        encoding="utf-8",
    )

    assert "required submission files changed after final submission commit" in validate_submission(tmp_path)


def test_strict_fixture_rejects_commit_mismatch(tmp_path: Path) -> None:
    metadata = _strict_fixture(tmp_path)
    metadata["final_submission_commit"] = "0" * 40
    (tmp_path / "submission-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    assert "checked-out commit does not match final submission commit" in validate_submission(tmp_path)
