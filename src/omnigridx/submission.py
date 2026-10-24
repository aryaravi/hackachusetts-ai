"""Deterministic validation for the judge delivery package."""

import argparse
import json
from pathlib import Path
import re
import subprocess
from typing import Any
from urllib.parse import urlparse

_PLACEHOLDER = re.compile(r"REPLACE|PLACEHOLDER|TODO", re.IGNORECASE)
_SHA256 = re.compile(r"[0-9a-f]{64}").fullmatch
_COMMIT = re.compile(r"[0-9a-f]{40}").fullmatch
_RENDER_HOST_SUFFIX = ".onrender.com"
_DRAFT_PUBLIC_URL = "REPLACE_WITH_RENDER_HTTPS_URL"
_DRAFT_FINGERPRINT = "REPLACE_AFTER_PUBLIC_MODE_RUN"
_DRAFT_COMMIT = "REPLACE_AT_SUBMISSION"
_DISCLOSURE_TERMS = {
    "cold_start": ("cold-start",),
    "ephemeral_storage": ("ephemeral", "no persistence"),
    "free_tier_volatility": ("free-tier", "change"),
    "local_fallback": ("make demo",),
}
_REQUIRED_FILES = (
    "LICENSE",
    "README.md",
    "SUBMISSION_WRITEUP.md",
    "THIRD_PARTY_NOTICES.md",
    "submission-metadata.json",
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
_REQUIRED_DOCUMENT_TEXT = {
    "README.md": (
        "python3.13 -m venv .venv",
        "python -m pip install -e '.[dev]'",
        "make demo",
        "make check",
        "constrained grid intelligence",
        "no ai, weather, or demand forecasting",
    ),
    "SUBMISSION_WRITEUP.md": (
        "constrained grid intelligence",
        "no ai, weather, or demand forecasting",
        ".kiro/specs/omnigridx/requirements.md",
        ".kiro/hooks/task_validation.py",
        "no quantitative workflow-effect measurement was collected",
    ),
}
_REQUIRED_KIRO_EVIDENCE = {
    ".kiro/specs/omnigridx/requirements.md",
    ".kiro/specs/omnigridx/design.md",
    ".kiro/specs/omnigridx/tasks.md",
    ".kiro/hooks/task-checks.json",
    ".kiro/hooks/task_validation.py",
    ".kiro/steering/task-validation.md",
}
_SECRET_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
)
_CUSTOMER_DATA_KEYS = {
    "account_number",
    "customer_address",
    "customer_email",
    "customer_name",
    "meter_id",
}
_EXECUTABLE_SUFFIXES = {".class", ".dll", ".dylib", ".exe", ".jar", ".so", ".wasm"}
_IGNORED_PARTS = {
    ".git",
    ".hypothesis",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
_TEXT_SUFFIXES = {".html", ".js", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}


def _https_url(value: Any) -> bool:
    if not isinstance(value, str) or _PLACEHOLDER.search(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username


def _render_https_base_url(value: Any) -> bool:
    if not _https_url(value):
        return False
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    return (
        host.endswith(_RENDER_HOST_SUFFIX)
        and parsed.port is None
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    )


def _expected_public_report_fingerprint() -> str:
    from omnigridx.infrastructure.sample import build_sample_report

    return build_sample_report("demo-public").fingerprint


def _repository_files(root: Path) -> tuple[Path, ...]:
    return tuple(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not any(part in _IGNORED_PARTS for part in path.relative_to(root).parts)
        and path.name != ".DS_Store"
    )


def _nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in _nested_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in _nested_keys(child)}
    return set()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )


def _kiro_is_ignored(root: Path, ignore: str) -> bool:
    result = _git(root, "check-ignore", ".kiro/hooks/task_validation.py")
    if result.returncode == 0:
        return True
    for raw_line in ignore.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        normalized = line.removeprefix("/").rstrip("/")
        if normalized.startswith(".kiro") or normalized.startswith("**/.kiro"):
            return True
    return False


def _validate_documentation(root: Path, issues: list[str]) -> None:
    for name, required_text in _REQUIRED_DOCUMENT_TEXT.items():
        path = root / name
        content = path.read_text(encoding="utf-8").lower() if path.is_file() else ""
        for text in required_text:
            if text not in content:
                issues.append(f"{name} missing required text: {text}")


def _validate_repository_content(root: Path, issues: list[str]) -> None:
    for path in _repository_files(root):
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() in _EXECUTABLE_SUFFIXES:
            issues.append(f"undeclared executable artifact: {relative}")
        if path.suffix.lower() not in _TEXT_SUFFIXES and not path.name.startswith(".env"):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in _SECRET_PATTERNS:
            if pattern.search(content):
                issues.append(f"known secret pattern ({label}) in {relative}")
        if "data" in path.parts and path.suffix.lower() == ".json":
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                continue
            customer_keys = sorted(_nested_keys(data) & _CUSTOMER_DATA_KEYS)
            if customer_keys:
                issues.append(
                    f"customer-data fields in bundled data {relative}: {', '.join(customer_keys)}"
                )


def _validate_git_state(
    root: Path, metadata: dict[str, Any], commit: str, issues: list[str]
) -> None:
    tracked_result = _git(root, "ls-files")
    if tracked_result.returncode:
        issues.append("repository tracked-file state could not be read")
        return
    tracked = set(tracked_result.stdout.splitlines())
    kiro_files = {
        path.relative_to(root).as_posix()
        for path in _repository_files(root)
        if path.relative_to(root).parts[0] == ".kiro"
    }
    for name in sorted(set(_REQUIRED_FILES) | kiro_files):
        if name not in tracked:
            issues.append(f"required file is not tracked: {name}")

    head_result = _git(root, "rev-parse", "HEAD")
    head = head_result.stdout.strip() if head_result.returncode == 0 else ""
    if head != commit:
        issues.append("checked-out commit does not match final submission commit")
        return

    immutable_paths = sorted((set(_REQUIRED_FILES) | kiro_files) - {"submission-metadata.json"})
    diff_result = _git(root, "diff", "--name-only", commit, "--", *immutable_paths)
    if diff_result.returncode or diff_result.stdout.strip():
        issues.append("required submission files changed after final submission commit")

    committed_result = _git(root, "show", f"{commit}:submission-metadata.json")
    if committed_result.returncode:
        issues.append("submission metadata is absent from final submission commit")
        return
    try:
        committed_metadata = json.loads(committed_result.stdout)
    except json.JSONDecodeError:
        issues.append("submission metadata in final submission commit is invalid")
        return
    if not isinstance(committed_metadata, dict):
        issues.append("submission metadata in final submission commit must be an object")
        return
    # The commit identifier cannot be embedded in the commit it identifies; this is the sole permitted post-commit field change.
    committed_metadata["final_submission_commit"] = metadata.get("final_submission_commit")
    if committed_metadata != metadata:
        issues.append("submission metadata changed after final commit beyond its commit field")


def validate_submission(root: Path, *, allow_draft: bool = False) -> tuple[str, ...]:
    issues: list[str] = []
    for name in _REQUIRED_FILES:
        if not (root / name).is_file():
            issues.append(f"missing required file: {name}")

    metadata_path = root / "submission-metadata.json"
    if not metadata_path.is_file():
        return tuple(issues)
    try:
        metadata_value = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return (*issues, f"invalid submission metadata: {error}")
    if not isinstance(metadata_value, dict):
        return (*issues, "submission metadata must be an object")
    metadata: dict[str, Any] = metadata_value

    if metadata.get("schema_version") != "1.0":
        issues.append("submission metadata schema_version must be 1.0")
    expected_status = "draft" if allow_draft else "submitted"
    if metadata.get("status") != expected_status:
        issues.append(f"submission metadata status must be {expected_status}")
    if metadata.get("track") != "Climate Tech & Clean Energy":
        issues.append("track must be Climate Tech & Clean Energy")
    if metadata.get("project_name") != "OmniGridX":
        issues.append("project name must be OmniGridX")
    if not str(metadata.get("project_description", "")).strip():
        issues.append("project description is required")
    if not _https_url(metadata.get("repository_url")):
        issues.append("public repository URL must be HTTPS")
    if metadata.get("third_party_notices") != "THIRD_PARTY_NOTICES.md":
        issues.append("third-party notices reference is required")
    if metadata.get("artifact_license") != "LICENSE":
        issues.append("artifact license reference is required")

    evidence = metadata.get("kiro_evidence")
    if not isinstance(evidence, list) or not _REQUIRED_KIRO_EVIDENCE.issubset(evidence):
        issues.append("Kiro evidence references are incomplete")
    elif any(not (root / name).is_file() for name in evidence if isinstance(name, str)):
        issues.append("Kiro evidence reference is missing")

    local = metadata.get("local_judge", {})
    if not isinstance(local, dict) or (
        local.get("command") != "make demo"
        or local.get("test_command") != "make check"
        or local.get("url") != "http://127.0.0.1:8000"
        or local.get("requires_login") is not False
        or local.get("accepts_user_data") is not False
    ):
        issues.append(
            "local judge path must be unrestricted make demo on loopback with make check and no user data"
        )

    data_policy = metadata.get("data_policy", {})
    if not isinstance(data_policy, dict) or (
        data_policy.get("input_scope") != "bundled synthetic non-customer sample only"
        or data_policy.get("uploads_enabled") is not False
        or data_policy.get("remote_adapters_enabled") is not False
        or data_policy.get("contains_secrets") is not False
        or data_policy.get("contains_customer_data") is not False
    ):
        issues.append("submission data policy must exclude secrets and customer or remote input")

    public = metadata.get("public_demo", {})
    if not isinstance(public, dict):
        public = {}
    if public.get("provider") != "Render":
        issues.append("public demo provider must be Render")
    base_url = public.get("base_url")
    if not (allow_draft and base_url == _DRAFT_PUBLIC_URL) and not _render_https_base_url(base_url):
        issues.append("public demo URL must be a Render HTTPS base URL or the draft placeholder")
    if public.get("health_path") != "/healthz":
        issues.append("public health path must be /healthz")
    if public.get("report_path") != "/api/sample-report":
        issues.append("public report path must be /api/sample-report")
    fingerprint = str(public.get("report_fingerprint", ""))
    if not (allow_draft and fingerprint == _DRAFT_FINGERPRINT):
        if _SHA256(fingerprint) is None:
            issues.append("public report fingerprint must be a SHA-256 value or the draft placeholder")
        elif fingerprint != _expected_public_report_fingerprint():
            issues.append(
                "public report fingerprint must match the deterministic demo-public report"
            )

    video = metadata.get("video", {})
    team = metadata.get("team_members", [])
    representative = metadata.get("authorized_representative")
    commit = str(metadata.get("final_submission_commit", ""))
    if allow_draft:
        if commit != _DRAFT_COMMIT and _COMMIT(commit) is None:
            issues.append("final submission commit must be a full Git commit or the draft placeholder")
    else:
        if not isinstance(team, list) or not 1 <= len(team) <= 4 or len(set(team)) != len(team):
            issues.append("team must contain one to four unique members")
        if representative not in team or metadata.get("representative_authorized") is not True:
            issues.append("authorized representative must be an authorized team member")
        if not isinstance(video, dict) or not _https_url(video.get("url")):
            issues.append("video URL must be populated HTTPS")
        else:
            host = (urlparse(video["url"]).hostname or "").lower()
            approved = tuple(video.get("approved_hosts", ()))
            if not any(
                isinstance(value, str) and (host == value or host.endswith("." + value))
                for value in approved
            ):
                issues.append("video URL host is not approved")
        duration = video.get("duration_seconds") if isinstance(video, dict) else None
        if (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not 0 < duration < 180
        ):
            issues.append("video duration must be greater than zero and less than 180 seconds")
        if _COMMIT(commit) is None:
            issues.append("final submission commit must be a full Git commit")
        else:
            _validate_git_state(root, metadata, commit, issues)

    notices_path = root / "THIRD_PARTY_NOTICES.md"
    notices = notices_path.read_text(encoding="utf-8") if notices_path.is_file() else ""
    for component in _REQUIRED_NOTICES:
        if component not in notices:
            issues.append(f"third-party notice missing: {component}")

    ignore_path = root / ".gitignore"
    ignore = ignore_path.read_text(encoding="utf-8") if ignore_path.is_file() else ""
    if _kiro_is_ignored(root, ignore):
        issues.append(".kiro content must not be ignored")

    disclosures = metadata.get("hosting_disclosures", {})
    if not isinstance(disclosures, dict):
        disclosures = {}
    for name, terms in _DISCLOSURE_TERMS.items():
        disclosure = str(disclosures.get(name, "")).lower()
        if not all(term in disclosure for term in terms):
            issues.append(f"invalid hosting disclosure: {name}")

    _validate_documentation(root, issues)
    _validate_repository_content(root, issues)
    return tuple(dict.fromkeys(issues))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    issues = validate_submission(args.root.resolve(), allow_draft=args.allow_draft)
    if issues:
        raise SystemExit("Submission validation failed:\n- " + "\n- ".join(issues))
    print("Submission package is valid." if not args.allow_draft else "Draft submission structure is valid.")


if __name__ == "__main__":
    main()
