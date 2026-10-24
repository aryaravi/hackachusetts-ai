from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

REQUIRED_SPEC_FILES = ("requirements.md", "design.md", "tasks.md", ".config.kiro")
TASK_LINE = re.compile(
    r"^(?P<indent> *)- \[(?P<status>[ xX~-])\](?P<optional>\*)? "
    r"(?P<id>\d+(?:\.\d+)*)(?:\.)? (?P<title>\S.*)$"
)
CHECKBOX_LINE = re.compile(r"^\s*- \[[^]]*\]\*? \d")
GRAPH = re.compile(r"## Task Dependency Graph\s*```json\s*(.*?)\s*```", re.DOTALL)
MAX_OUTPUT = 4_000


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    status: str
    optional: bool

    @property
    def identity(self) -> str:
        return f"{self.task_id} {self.title}"


@dataclass(frozen=True)
class CheckResult:
    returncode: int
    output: str = ""


Runner = Callable[[Sequence[str], Path, int], CheckResult]


def parse_tasks(text: str) -> tuple[list[Task], list[list[str]]]:
    tasks: list[Task] = []
    seen_ids: set[str] = set()
    for number, line in enumerate(text.splitlines(), 1):
        match = TASK_LINE.match(line)
        if not match:
            if CHECKBOX_LINE.match(line):
                raise ValidationError(f"malformed task checkbox at line {number}")
            continue

        task_id = match.group("id")
        depth = task_id.count(".")
        if len(match.group("indent")) != depth * 2:
            raise ValidationError(f"invalid task hierarchy at line {number}")
        if task_id in seen_ids:
            raise ValidationError(f"ambiguous duplicate task id: {task_id}")
        seen_ids.add(task_id)
        tasks.append(
            Task(
                task_id=task_id,
                title=match.group("title"),
                status=match.group("status").lower(),
                optional=bool(match.group("optional")),
            )
        )

    if not tasks:
        raise ValidationError("tasks.md contains no tasks")
    ids = {task.task_id for task in tasks}
    for task in tasks:
        if "." in task.task_id and task.task_id.rsplit(".", 1)[0] not in ids:
            raise ValidationError(f"task {task.task_id} has no parent")

    graph_match = GRAPH.search(text)
    if not graph_match:
        raise ValidationError("tasks.md has no valid dependency graph")
    try:
        graph_data = json.loads(graph_match.group(1))
        waves = graph_data["waves"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValidationError("tasks.md dependency graph is malformed") from error
    if not isinstance(waves, list):
        raise ValidationError("tasks.md dependency waves must be a list")

    graph_waves: list[list[str]] = []
    graph_ids: list[str] = []
    for expected_wave, wave in enumerate(waves):
        if not isinstance(wave, dict) or wave.get("id") != expected_wave:
            raise ValidationError("dependency wave ids must be consecutive")
        wave_tasks = wave.get("tasks")
        if not isinstance(wave_tasks, list) or not all(isinstance(item, str) for item in wave_tasks):
            raise ValidationError(f"dependency wave {expected_wave} has invalid tasks")
        graph_waves.append(wave_tasks)
        graph_ids.extend(wave_tasks)

    leaf_ids = {
        task.task_id
        for task in tasks
        if not any(other.task_id.startswith(f"{task.task_id}.") for other in tasks)
    }
    if len(graph_ids) != len(set(graph_ids)) or set(graph_ids) != leaf_ids:
        raise ValidationError("dependency graph must contain every leaf task exactly once")
    return tasks, graph_waves


def require_spec_files(root: Path) -> Path:
    spec_dir = root / ".kiro" / "specs" / "omnigridx"
    missing = [name for name in REQUIRED_SPEC_FILES if not (spec_dir / name).is_file()]
    if missing:
        raise ValidationError(f"missing required spec files: {', '.join(missing)}")
    return spec_dir


def string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in string_values(child)]
    if isinstance(value, list):
        return [item for child in value for item in string_values(child)]
    return []


def select_task(event: object, tasks: list[Task]) -> Task:
    identities = {task.identity: task for task in tasks}
    matches = {value for value in string_values(event) if value in identities}
    if len(matches) != 1:
        raise ValidationError("hook event must contain one exact leaf-task identity")
    task = identities[matches.pop()]
    if any(other.task_id.startswith(f"{task.task_id}.") for other in tasks):
        raise ValidationError(f"task is not a leaf: {task.identity}")
    if task.status == "x":
        raise ValidationError(f"task is already complete: {task.identity}")
    return task


def validate_pre(root: Path, event: object) -> Task:
    spec_dir = require_spec_files(root)
    tasks, waves = parse_tasks((spec_dir / "tasks.md").read_text(encoding="utf-8"))
    task = select_task(event, tasks)
    task_by_id = {item.task_id: item for item in tasks}
    task_wave = next(index for index, wave in enumerate(waves) if task.task_id in wave)
    blocked = [
        task_by_id[task_id].identity
        for wave in waves[:task_wave]
        for task_id in wave
        if task_by_id[task_id].status != "x"
    ]
    if blocked:
        raise ValidationError(f"incomplete prior-wave dependencies: {', '.join(blocked)}")
    return task


def local_runner(argv: Sequence[str], root: Path, timeout_seconds: int) -> CheckResult:
    environment = os.environ.copy()
    environment.update({"PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INDEX": "1"})
    virtualenv_bin = root / ".venv" / "bin"
    if virtualenv_bin.is_dir():
        environment["PATH"] = f"{virtualenv_bin}{os.pathsep}{environment.get('PATH', '')}"
    try:
        completed = subprocess.run(
            argv,
            cwd=root,
            check=False,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=timeout_seconds,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return CheckResult(1, str(error))
    return CheckResult(completed.returncode, completed.stdout + completed.stderr)


def validate_post(root: Path, event: object, runner: Runner = local_runner) -> Task:
    spec_dir = require_spec_files(root)
    tasks, _ = parse_tasks((spec_dir / "tasks.md").read_text(encoding="utf-8"))
    task = select_task(event, tasks)
    config_path = root / ".kiro" / "hooks" / "task-checks.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        checks = config[task.identity]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValidationError(f"no valid post-task checks configured for {task.identity}") from error
    if not isinstance(checks, list) or not checks:
        raise ValidationError(f"no post-task checks configured for {task.identity}")

    for check in checks:
        if not isinstance(check, dict):
            raise ValidationError("post-task check entry must be an object")
        name, argv, timeout_seconds = check.get("name"), check.get("argv"), check.get("timeout_seconds")
        if (
            not isinstance(name, str)
            or not isinstance(argv, list)
            or not argv
            or not all(isinstance(arg, str) and arg for arg in argv)
            or not isinstance(timeout_seconds, int)
            or not 1 <= timeout_seconds <= 300
        ):
            raise ValidationError(f"invalid post-task check for {task.identity}")
        result = runner(argv, root, timeout_seconds)
        if result.returncode:
            output = result.output[-MAX_OUTPUT:].strip()
            detail = f": {output}" if output else ""
            raise ValidationError(f"post-task check failed ({name}){detail}")
    return task


def fixture_tasks(prior_complete: bool = True, duplicate: bool = False) -> str:
    first_status = "x" if prior_complete else " "
    duplicate_line = "\n  - [ ] 1.2 Current task" if duplicate else ""
    return f"""# Tasks

- [ ] 1 Parent
  - [{first_status}] 1.1 Prior task
  - [ ] 1.2 Current task{duplicate_line}

## Task Dependency Graph

```json
{{"waves": [{{"id": 0, "tasks": ["1.1"]}}, {{"id": 1, "tasks": ["1.2"]}}]}}
```
"""


def write_fixture(root: Path, tasks_text: str) -> None:
    spec_dir = root / ".kiro" / "specs" / "omnigridx"
    spec_dir.mkdir(parents=True)
    for name in REQUIRED_SPEC_FILES:
        (spec_dir / name).write_text(tasks_text if name == "tasks.md" else "fixture", encoding="utf-8")


def expect_failure(action: Callable[[], object], message: str) -> None:
    try:
        action()
    except ValidationError:
        return
    raise AssertionError(message)


def self_check() -> None:
    identity = "1.2 Current task"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_fixture(root, fixture_tasks())
        assert validate_pre(root, {"task": identity}).identity == identity
        expect_failure(lambda: validate_pre(root, {"task": "9.9 Unknown"}), "unknown task allowed")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_fixture(root, fixture_tasks(duplicate=True))
        expect_failure(lambda: validate_pre(root, {"task": identity}), "ambiguous tasks allowed")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_fixture(root, fixture_tasks(prior_complete=False))
        expect_failure(lambda: validate_pre(root, {"task": identity}), "blocked dependency allowed")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_fixture(root, fixture_tasks())
        hooks_dir = root / ".kiro" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "task-checks.json").write_text(
            json.dumps({identity: [{"name": "target", "argv": ["local-check"], "timeout_seconds": 1}]}),
            encoding="utf-8",
        )
        failing_runner: Runner = lambda argv, cwd, timeout: CheckResult(1, "expected failure")
        expect_failure(
            lambda: validate_post(root, {"task": identity}, failing_runner),
            "failed post-task command allowed",
        )


def load_event() -> object:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as error:
        raise ValidationError("hook input must be JSON") from error


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    try:
        if mode == "self-check":
            self_check()
            print("task hook self-check passed")
            return 0
        root = Path(__file__).resolve().parents[2]
        event = load_event()
        task = validate_pre(root, event) if mode == "pre" else validate_post(root, event) if mode == "post" else None
        if task is None:
            raise ValidationError("usage: task_validation.py pre|post|self-check")
        print(f"task validation passed: {task.identity}")
        return 0
    except ValidationError as error:
        print(f"task validation blocked: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
