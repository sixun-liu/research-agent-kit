#!/usr/bin/env python3
"""Record a low-friction checkpoint for an active research experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state_lib import (
    TERMINAL_EXPERIMENT_STATUSES,
    VALID_PROGRESS_TYPES,
    append_jsonl,
    elapsed_hours,
    experiment_records,
    latest_experiment_state,
    load_jsonl,
    next_id,
    resolve_experiment_id,
    utc_now,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--experiment-id")
    parser.add_argument("--note", required=True)
    parser.add_argument("--progress-type", choices=sorted(VALID_PROGRESS_TYPES), default="none")
    parser.add_argument("--compute-hours-delta", type=float, default=0.0)
    parser.add_argument("--artifact-id", action="append", default=[])
    parser.add_argument(
        "--action-status",
        choices=("pending", "occurred", "absent", "not_applicable"),
        default="pending",
    )
    parser.add_argument(
        "--completion-status",
        choices=("pending", "confirmed", "failed", "not_applicable"),
        default="pending",
    )
    args = parser.parse_args()
    if args.compute_hours_delta < 0:
        raise SystemExit("--compute-hours-delta must be non-negative")

    root = args.root.resolve()
    experiment_id = resolve_experiment_id(root, args.experiment_id)
    experiments, events = experiment_records(root)
    experiment = experiments[experiment_id]
    latest = latest_experiment_state(experiment, events)
    if latest.get("status") in TERMINAL_EXPERIMENT_STATUSES:
        raise SystemExit(f"Experiment is already terminal: {experiment_id}")
    experiment_events = [
        event for event in events if event.get("experiment_id") == experiment_id
    ]
    if int(experiment.get("schema_version", 1)) >= 2 and not any(
        event.get("event_type") == "provenance_freeze" for event in experiment_events
    ):
        raise SystemExit("Freeze provenance before recording a runtime checkpoint")

    known_artifacts = {
        str(record.get("id"))
        for record in load_jsonl(root / "research" / "artifacts.jsonl")
        if record.get("record_type") == "artifact"
    }
    unknown_artifacts = sorted(set(args.artifact_id) - known_artifacts)
    if unknown_artifacts:
        raise SystemExit(f"Unknown artifact ids: {', '.join(unknown_artifacts)}")

    registry = root / "research" / "experiments.jsonl"
    event = {
        "record_type": "experiment_event",
        "schema_version": 3,
        "id": next_id(registry, "EVT"),
        "experiment_id": experiment_id,
        "created_at": utc_now(),
        "event_type": "checkpoint",
        "note": args.note,
        "progress_type": args.progress_type,
        "compute_hours_delta": args.compute_hours_delta,
        "wall_hours_since_start": elapsed_hours(str(experiment.get("created_at"))),
        "expected_action_status": args.action_status,
        "completion_signal_status": args.completion_status,
        "artifacts": args.artifact_id,
    }
    append_jsonl(registry, event)

    card = root / "research" / "cards" / f"{experiment_id}.md"
    if card.exists():
        with card.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n## Checkpoint\n\n"
                f"- 进展：`{args.progress_type}`；{args.note}\n"
                f"- 本段 compute：`{args.compute_hours_delta:.3f}h`\n"
                f"- 动作：`{args.action_status}`；完成信号：`{args.completion_status}`\n"
            )
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
