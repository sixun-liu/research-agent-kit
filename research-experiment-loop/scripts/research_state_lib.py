#!/usr/bin/env python3
"""Shared helpers for the research experiment lifecycle commands."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REGISTRIES = {
    "experiments.jsonl": "EXP",
    "insights.jsonl": "I",
    "claims.jsonl": "C",
    "artifacts.jsonl": "ART",
}
TERMINAL_EXPERIMENT_STATUSES = {"complete", "archived", "blocked"}
VALID_CONFIRMATIONS = {"pending", "confirmed", "disagreed", "not_required"}
VALID_STAGES = {"exploration", "attack", "convergence", "writing", "complete"}
VALID_DECISIONS = {
    "promote",
    "promising_unresolved",
    "needs_more_evidence",
    "negative",
    "inconclusive",
    "invalid_provenance",
}
VALID_WORK_MODES = {"theory", "practice", "mixed", "instrumentation"}
VALID_PROGRESS_TYPES = {"metric", "uncertainty_reduction", "route_closed", "efficiency", "none"}
VALID_TASK_ACTIONS = {
    "INTEGRITY",
    "BREAKTHROUGH",
    "REFLECT",
    "INTUITION",
    "THEORY_SYNC",
    "PRACTICE_SYNC",
    "SYNTHESIS",
    "HUMAN_REVIEW",
    "EFFICIENCY_REVIEW",
}
TERMINAL_TASK_STATUSES = {"complete", "cancelled", "waived", "merged"}
VALID_TASK_EVENT_STATUSES = TERMINAL_TASK_STATUSES | {"deferred"}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def elapsed_hours(start: str, end: str | None = None) -> float:
    end_value = parse_utc(end) if end else dt.datetime.now(dt.timezone.utc)
    return max(0.0, (end_value - parse_utc(start)).total_seconds() / 3600.0)


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML is required for research state commands") from exc
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a YAML mapping: {path}")
    return value


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML is required for research state commands") from exc
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise SystemExit(f"{path}:{number}: expected an object")
        records.append(value)
    return records


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def next_id(path: Path, prefix: str) -> str:
    maximum = 0
    for record in load_jsonl(path):
        value = str(record.get("id", ""))
        if not value.startswith(f"{prefix}-"):
            continue
        suffix = value.removeprefix(f"{prefix}-")
        if suffix.isdigit():
            maximum = max(maximum, int(suffix))
    return f"{prefix}-{maximum + 1:04d}"


def experiment_records(root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    records = load_jsonl(root / "research" / "experiments.jsonl")
    experiments = {
        str(record["id"]): record
        for record in records
        if record.get("record_type") == "experiment" and record.get("id")
    }
    events = [record for record in records if record.get("record_type") == "experiment_event"]
    return experiments, events


def task_records(root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    path = root / "research" / "tasks.jsonl"
    if not path.exists():
        return {}, []
    records = load_jsonl(path)
    tasks = {
        str(record["id"]): record
        for record in records
        if record.get("record_type") == "research_task" and record.get("id")
    }
    events = [record for record in records if record.get("record_type") == "task_event"]
    return tasks, events


def latest_experiment_state(
    experiment: dict[str, Any], events: list[dict[str, Any]]
) -> dict[str, Any]:
    value = dict(experiment)
    for event in sorted(
        events,
        key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")),
    ):
        if event.get("experiment_id") != experiment.get("id"):
            continue
        for key in ("status", "verdict", "decision", "human_visual_confirmation"):
            if event.get(key) is not None:
                value[key] = event[key]
        value["updated_at"] = event.get("created_at", value.get("updated_at"))
    return value


def latest_task_state(task: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    value = dict(task)
    for event in sorted(
        events,
        key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")),
    ):
        if event.get("task_id") != task.get("id"):
            continue
        for key in (
            "status",
            "result",
            "artifact_ids",
            "insight_ids",
            "resume_condition",
            "merge_into",
        ):
            if event.get(key) is not None:
                value[key] = event[key]
        value["updated_at"] = event.get("created_at", value.get("updated_at"))
    return value


def resolve_experiment_id(root: Path, requested: str | None) -> str:
    state = load_yaml(root / "research" / "project_state.yaml")
    experiment_id = requested or state.get("active_experiment_id")
    if not experiment_id:
        raise SystemExit("No experiment id supplied and project has no active experiment")
    experiments, _ = experiment_records(root)
    if experiment_id not in experiments:
        raise SystemExit(f"Unknown experiment id: {experiment_id}")
    return str(experiment_id)


def git_snapshot(repo: Path) -> dict[str, Any]:
    def run(*args: str) -> tuple[int, str]:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        return result.returncode, result.stdout.strip()

    code, commit = run("rev-parse", "HEAD")
    if code:
        raise SystemExit(f"Canonical repo is not a usable Git repository: {repo}")
    _, branch = run("rev-parse", "--abbrev-ref", "HEAD")
    _, tracked = run("status", "--porcelain", "--untracked-files=no")
    return {
        "repo": str(repo.resolve()),
        "branch": branch or "unknown",
        "commit": commit,
        "tracked_clean": tracked == "",
    }


def canonical_repo(root: Path, state: dict[str, Any] | None = None) -> Path:
    state = state or load_yaml(root / "research" / "project_state.yaml")
    value = state.get("canonical_repo", {})
    if not isinstance(value, dict) or not value.get("path"):
        raise SystemExit("project_state.yaml lacks canonical_repo.path")
    return Path(str(value["path"])).resolve()


def update_project_state(root: Path, **changes: Any) -> dict[str, Any]:
    path = root / "research" / "project_state.yaml"
    state = load_yaml(path)
    state.update(changes)
    state["updated_at"] = utc_now()
    write_yaml(path, state)
    return state


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_project_path(root: Path, value: Path) -> Path:
    return value.resolve() if value.is_absolute() else (root / value).resolve()
