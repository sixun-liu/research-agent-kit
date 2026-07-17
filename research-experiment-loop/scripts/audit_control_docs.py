#!/usr/bin/env python3
"""Read-only audit for hot control documents and human-review pointers."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from research_state_lib import (
    TERMINAL_EXPERIMENT_STATUSES,
    experiment_records,
    latest_experiment_state,
    load_yaml,
)


DOCS: dict[str, dict[str, Any]] = {
    "CURRENT_STATE.md": {
        "headings": ("## 一句话判断", "## 当前主要矛盾", "## 下一项决策"),
        "max_lines": 60,
        "source": "research/project_state.yaml and research/experiments.jsonl",
    },
    "PLAN.md": {
        "headings": ("## 阶段退出门", "## 活动路线", "## Parked Lanes"),
        "max_lines": 120,
        "source": "research/project_state.yaml",
    },
    "TODO.md": {
        "headings": ("## Now", "## Waiting"),
        "max_lines": 80,
        "source": "manual action view; long-lived tasks use research/tasks.jsonl",
    },
    "DEVLOG.md": {
        "headings": (),
        "max_lines": 400,
        "source": "decision synthesis linked to research IDs",
    },
    "RESULTS_SCOREBOARD.md": {
        "headings": (),
        "max_lines": 300,
        "source": "research/experiments.jsonl and research/artifacts.jsonl",
    },
}

TIMESTAMP_RE = re.compile(r"^> Updated: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$", re.MULTILINE)
MAINTAINER_RE = re.compile(r"^> Maintainer: (\S.+)$", re.MULTILINE)
SOURCE_RE = re.compile(r"^> Source of truth: (\S.+)$", re.MULTILINE)
EVENT_RE = re.compile(
    r"^### (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) \| "
    r"(decision|protocol|result|migration|workflow) \| (\S.+)$",
    re.MULTILINE,
)
EVENT_FIELDS = ("Actor", "Summary", "Evidence", "Next")


def audit_devlog(text: str, warnings: list[str]) -> None:
    matches = list(EVENT_RE.finditer(text))
    if not matches and re.search(r"^## \d{4}-\d{2}-\d{2}$", text, re.MULTILINE):
        warnings.append("DEVLOG.md has dated content but no structured event headings")
        return
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end() : end]
        missing = [field for field in EVENT_FIELDS if f"- {field}:" not in section]
        if missing:
            warnings.append(
                f"DEVLOG.md event {match.group(1)} {match.group(3)} lacks: {', '.join(missing)}"
            )


def pending_reviews(root: Path) -> list[str]:
    try:
        experiments, events = experiment_records(root)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    result = []
    for experiment_id, experiment in experiments.items():
        latest = latest_experiment_state(experiment, events)
        if (
            latest.get("status") in TERMINAL_EXPERIMENT_STATUSES
            and latest.get("human_visual_confirmation") == "pending"
        ):
            result.append(experiment_id)
    return sorted(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    summaries: dict[str, dict[str, Any]] = {}
    state_path = root / "research" / "project_state.yaml"
    state = load_yaml(state_path) if state_path.exists() else {}

    for filename, contract in DOCS.items():
        path = root / filename
        if not path.is_file():
            errors.append(f"missing control document: {filename}")
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        summaries[filename] = {"lines": len(lines)}
        if not TIMESTAMP_RE.search(text):
            errors.append(f"{filename} lacks UTC Updated metadata")
        if not MAINTAINER_RE.search(text):
            errors.append(f"{filename} lacks Maintainer metadata")
        source = SOURCE_RE.search(text)
        if not source:
            errors.append(f"{filename} lacks Source of truth metadata")
        elif source.group(1) != contract["source"]:
            warnings.append(f"{filename} uses a nonstandard Source of truth")
        for heading in contract["headings"]:
            if heading not in text:
                errors.append(f"{filename} lacks required heading: {heading}")
        if len(lines) > int(contract["max_lines"]):
            warnings.append(
                f"{filename} has {len(lines)} lines; review threshold is {contract['max_lines']}"
            )
        if filename == "PLAN.md" and state.get("stage"):
            marker = f"- Stage: `{state['stage']}`"
            if marker not in text:
                warnings.append(f"PLAN.md does not show current project stage {state['stage']}")
        if filename == "TODO.md":
            completed = len(re.findall(r"^- \[[xX]\]", text, re.MULTILINE))
            summaries[filename]["completed_items"] = completed
            if completed > 3:
                warnings.append(
                    f"TODO.md retains {completed} completed items; move persistent decisions to DEVLOG"
                )
        if filename == "DEVLOG.md":
            audit_devlog(text, warnings)

    pending = pending_reviews(root)
    review = state.get("human_review", {}) if isinstance(state.get("human_review"), dict) else {}
    latest_value = review.get("latest")
    latest_path = None
    if latest_value:
        latest_path = Path(str(latest_value)).expanduser()
        if not latest_path.is_absolute():
            latest_path = root / latest_path
    if pending:
        if not latest_path or not latest_path.is_file():
            warnings.append(f"pending human review lacks LATEST.md pointer: {', '.join(pending)}")
        else:
            latest_text = latest_path.read_text(encoding="utf-8")
            if "pending" not in latest_text or not any(value in latest_text for value in pending):
                warnings.append(
                    "LATEST.md does not point to a pending experiment: " + ", ".join(pending)
                )
    elif latest_path and latest_path.is_file():
        latest_text = latest_path.read_text(encoding="utf-8")
        if "pending" in latest_text:
            warnings.append("LATEST.md says pending but registry has no pending human review")

    result = {
        "root": str(root),
        "documents": summaries,
        "pending_human_reviews": pending,
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
        "strict_ok": not errors and not warnings,
    }
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Control docs: {root}")
        print(f"Errors: {len(errors)}; warnings: {len(warnings)}")
        for value in errors:
            print(f"ERROR: {value}")
        for value in warnings:
            print(f"WARN: {value}")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())

