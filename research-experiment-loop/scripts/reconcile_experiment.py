#!/usr/bin/env python3
"""Reconcile an orphan experiment without inventing a scientific verdict."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state_lib import (
    TERMINAL_EXPERIMENT_STATUSES,
    append_jsonl,
    experiment_records,
    latest_experiment_state,
    load_yaml,
    next_id,
    resolve_project_path,
    update_project_state,
    utc_now,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_id")
    parser.add_argument("--root", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--adopt", action="store_true")
    action.add_argument("--complete-legacy", action="store_true")
    action.add_argument("--archive-legacy", action="store_true")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--verdict")
    parser.add_argument("--evidence-path", type=Path, action="append", default=[])
    args = parser.parse_args()

    root = args.root.resolve()
    experiments, events = experiment_records(root)
    if args.experiment_id not in experiments:
        raise SystemExit(f"Unknown experiment id: {args.experiment_id}")
    experiment = experiments[args.experiment_id]
    latest = latest_experiment_state(experiment, events)
    current_status = str(latest.get("status") or "preregistered")
    if current_status in TERMINAL_EXPERIMENT_STATUSES:
        raise SystemExit(f"Experiment is already terminal: {args.experiment_id}")

    state = load_yaml(root / "research" / "project_state.yaml")
    active_id = state.get("active_experiment_id")
    if args.adopt:
        if active_id and active_id != args.experiment_id:
            raise SystemExit(f"Another experiment is active: {active_id}")
        action_name = "adopt"
        status = current_status
        verdict = latest.get("verdict")
        evidence_paths: list[str] = []
    else:
        if int(experiment.get("schema_version", 1)) >= 2:
            raise SystemExit(
                "Modern experiments must use the formal close path; legacy reconciliation is forbidden"
            )
        if args.complete_legacy:
            if not args.verdict:
                raise SystemExit("--complete-legacy requires --verdict")
            if not args.evidence_path:
                raise SystemExit("--complete-legacy requires at least one --evidence-path")
            action_name = "complete_legacy"
            status = "complete"
            verdict = args.verdict
        else:
            action_name = "archive_legacy"
            status = "archived"
            verdict = "legacy_state_archived_without_scientific_reinterpretation"
        evidence_paths = []
        for value in args.evidence_path:
            path = resolve_project_path(root, value)
            if not path.exists():
                raise SystemExit(f"Reconciliation evidence does not exist: {path}")
            evidence_paths.append(str(path))

    registry = root / "research" / "experiments.jsonl"
    event = {
        "record_type": "experiment_event",
        "schema_version": 3,
        "id": next_id(registry, "EVT"),
        "experiment_id": args.experiment_id,
        "created_at": utc_now(),
        "event_type": "state_reconciliation",
        "reconciliation_action": action_name,
        "previous_status": current_status,
        "status": status,
        "verdict": verdict,
        "reason": args.reason,
        "evidence_paths": evidence_paths,
        "scientific_reinterpretation": False,
    }
    append_jsonl(registry, event)
    if args.adopt:
        update_project_state(root, active_experiment_id=args.experiment_id)
    elif active_id == args.experiment_id:
        update_project_state(root, active_experiment_id=None)

    card = root / "research" / "cards" / f"{args.experiment_id}.md"
    if card.exists():
        with card.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n## 状态对账\n\n"
                f"- 动作：`{action_name}`\n"
                f"- 原状态：`{current_status}`；新状态：`{status}`\n"
                f"- 原因：{args.reason}\n"
                "- 该事件只修复控制面，不新增科学解释。\n"
            )
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
