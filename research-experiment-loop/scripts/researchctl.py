#!/usr/bin/env python3
"""Unified entry point and dynamic index for the research experiment loop."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from research_state_lib import (
    experiment_records,
    latest_experiment_state,
    latest_task_state,
    load_jsonl,
    task_records,
)


SCRIPT_COMMANDS = {
    "init": "init_research_state.py",
    "stage": "set_project_stage.py",
    "status": "research_status.py",
    "audit": "audit_research_state.py",
    "new": "new_experiment.py",
    "freeze": "freeze_experiment.py",
    "checkpoint": "record_checkpoint.py",
    "observe": "record_observation.py",
    "artifact": "register_artifact.py",
    "claim": "register_claim.py",
    "close": "close_experiment.py",
    "schedule": "evaluate_research_scheduler.py",
    "task": "complete_research_task.py",
    "reconcile": "reconcile_experiment.py",
    "relocate": "relocate_project.py",
}
QUERY_COMMANDS = {"list", "show", "find", "next"}


def print_help() -> None:
    commands = " ".join(sorted(SCRIPT_COMMANDS | {name: "" for name in QUERY_COMMANDS}))
    print(
        "Research Experiment Loop\n\n"
        "Usage: researchctl.py <command> [args]\n\n"
        f"Commands: {commands}\n\n"
        "The project root defaults to the current directory. Use '<command> --help' for details."
    )


def with_default_root(args: list[str]) -> list[str]:
    if any(value == "--root" or value.startswith("--root=") for value in args):
        return args
    return ["--root", str(Path.cwd()), *args]


def run_script(name: str, args: list[str]) -> int:
    script = Path(__file__).with_name(name)
    completed = subprocess.run([sys.executable, str(script), *with_default_root(args)], check=False)
    return completed.returncode


def load_rows(root: Path, kind: str) -> list[dict[str, Any]]:
    research = root / "research"
    if kind == "experiments":
        experiments, events = experiment_records(root)
        rows = []
        for experiment in experiments.values():
            latest = latest_experiment_state(experiment, events)
            rows.append(latest)
        return rows
    if kind == "tasks":
        tasks, events = task_records(root)
        return [latest_task_state(task, events) for task in tasks.values()]
    filename = {
        "artifacts": "artifacts.jsonl",
        "claims": "claims.jsonl",
        "insights": "insights.jsonl",
    }[kind]
    expected_type = kind.removesuffix("s")
    return [
        record
        for record in load_jsonl(research / filename)
        if record.get("record_type") == expected_type
    ]


def filter_rows(rows: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    filters = {
        "hypothesis_family": args.family,
        "decision": args.decision,
        "cycle_class": args.cycle_class,
        "status": args.status,
        "experiment_id": args.experiment_id,
        "action_type": args.action,
        "kind": args.kind_filter,
    }
    selected = [
        row
        for row in rows
        if all(
            expected is None or str(row.get(field)) == expected
            for field, expected in filters.items()
        )
    ]
    selected.sort(key=lambda row: str(row.get("created_at") or row.get("id") or ""), reverse=True)
    return selected[: args.limit] if args.limit else selected


def compact_row(kind: str, row: dict[str, Any]) -> str:
    if kind == "experiments":
        return "\t".join(
            str(value or "-")
            for value in (
                row.get("id"),
                row.get("status"),
                row.get("decision"),
                row.get("cycle_class", "formal"),
                row.get("hypothesis_family"),
                row.get("title"),
            )
        )
    if kind == "artifacts":
        return "\t".join(
            str(value or "-")
            for value in (
                row.get("id"),
                row.get("kind"),
                row.get("experiment_id"),
                row.get("title"),
                row.get("path"),
            )
        )
    if kind == "claims":
        return "\t".join(
            str(value or "-")
            for value in (row.get("id"), row.get("status"), row.get("scope"), row.get("claim"))
        )
    if kind == "tasks":
        return "\t".join(
            str(value or "-")
            for value in (
                row.get("id"),
                row.get("status"),
                row.get("priority"),
                row.get("action_type"),
            )
        )
    return "\t".join(
        str(value or "-")
        for value in (
            row.get("id"),
            row.get("created_at"),
            row.get("observation") or row.get("claim"),
        )
    )


def list_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="researchctl.py list")
    parser.add_argument("kind", choices=("experiments", "artifacts", "claims", "insights", "tasks"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--family")
    parser.add_argument("--decision")
    parser.add_argument("--cycle-class")
    parser.add_argument("--status")
    parser.add_argument("--experiment-id")
    parser.add_argument("--action")
    parser.add_argument("--kind", dest="kind_filter")
    parser.add_argument("--limit", type=int, default=20, help="0 means unlimited")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    rows = filter_rows(load_rows(args.root.resolve(), args.kind), args)
    if args.json_output:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(compact_row(args.kind, row))
    return 0


def registry_records(root: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for path in sorted((root / "research").glob("*.jsonl")):
        result[path.name] = load_jsonl(path)
    return result


def show_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="researchctl.py show")
    parser.add_argument("record_id")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args(argv)
    records = registry_records(args.root.resolve())
    reference_fields = {
        "artifact_ids",
        "artifacts",
        "claim_ids",
        "evidence",
        "evidence_ids",
        "insight_ids",
        "source_ids",
    }

    def related(record: dict[str, Any]) -> bool:
        if record.get("id") == args.record_id:
            return True
        if record.get("experiment_id") == args.record_id or record.get("task_id") == args.record_id:
            return True
        return any(args.record_id in (record.get(field) or []) for field in reference_fields)

    matches = [
        {"registry": registry, "record": record}
        for registry, rows in records.items()
        for record in rows
        if related(record)
    ]
    if not matches:
        raise SystemExit(f"Unknown research id: {args.record_id}")
    if args.full:
        print(json.dumps({"id": args.record_id, "matches": matches}, ensure_ascii=False, indent=2))
        return 0
    primary = next(
        (match["record"] for match in matches if match["record"].get("id") == args.record_id),
        {},
    )
    events = [
        match["record"]
        for match in matches
        if match["record"].get("record_type") in {"experiment_event", "task_event"}
    ]
    events.sort(key=lambda value: str(value.get("created_at") or ""))
    related_ids = {
        record_type: [
            str(match["record"].get("id"))
            for match in matches
            if match["record"].get("record_type") == record_type
            and match["record"].get("id") != args.record_id
        ]
        for record_type in ("artifact", "claim", "insight", "research_task")
    }
    latest_event = events[-1] if events else None
    latest_event_summary = (
        {
            key: latest_event.get(key)
            for key in ("id", "created_at", "status", "decision", "verdict", "next")
            if latest_event.get(key) is not None
        }
        if latest_event
        else None
    )
    summary = {
        "id": args.record_id,
        "record_type": primary.get("record_type"),
        "title": primary.get("title") or primary.get("claim") or primary.get("action_type"),
        "status": (events[-1].get("status") if events else None) or primary.get("status"),
        "decision": (events[-1].get("decision") if events else None) or primary.get("decision"),
        "verdict": (events[-1].get("verdict") if events else None) or primary.get("verdict"),
        "latest_event": latest_event_summary,
        "event_count": len(events),
        "related_ids": related_ids,
    }
    if args.json_output:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"{summary['id']}\t{summary['record_type'] or '-'}\t{summary['status'] or '-'}")
        print(f"Title: {summary['title'] or '-'}")
        print(f"Decision: {summary['decision'] or '-'}; verdict: {summary['verdict'] or '-'}")
        print(
            "Related: "
            + ", ".join(f"{name}={len(ids)}" for name, ids in related_ids.items())
            + f", events={len(events)}"
        )
        if events:
            print(f"Latest event: {events[-1].get('id')} at {events[-1].get('created_at')}")
    return 0


def find_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="researchctl.py find")
    parser.add_argument("text")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    needle = args.text.casefold()
    matches = []
    for registry, rows in registry_records(args.root.resolve()).items():
        for record in rows:
            if needle in json.dumps(record, ensure_ascii=False).casefold():
                matches.append({"registry": registry, "record": record})
    matches.sort(
        key=lambda match: str(
            match["record"].get("created_at") or match["record"].get("id") or ""
        ),
        reverse=True,
    )
    if args.limit:
        matches = matches[: args.limit]
    if args.json_output:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
    else:
        for match in matches:
            record = match["record"]
            print(
                f"{match['registry']}\t{record.get('id', '-')}\t"
                f"{record.get('record_type', '-')}"
            )
    return 0


def next_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="researchctl.py next")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    script = Path(__file__).with_name("research_status.py")
    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(args.root.resolve()), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        sys.stderr.write(completed.stderr)
        return completed.returncode
    next_action = json.loads(completed.stdout)["next_action"]
    if args.json_output:
        print(json.dumps(next_action, ensure_ascii=False, indent=2))
    else:
        print(f"{next_action['action']}: {next_action['reason']}")
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "help"}:
        print_help()
        return 0
    command, args = sys.argv[1], sys.argv[2:]
    if command in SCRIPT_COMMANDS:
        return run_script(SCRIPT_COMMANDS[command], args)
    if command == "list":
        return list_command(args)
    if command == "show":
        return show_command(args)
    if command == "find":
        return find_command(args)
    if command == "next":
        return next_command(args)
    raise SystemExit(f"Unknown command: {command}. Run researchctl.py --help.")


if __name__ == "__main__":
    raise SystemExit(main())
