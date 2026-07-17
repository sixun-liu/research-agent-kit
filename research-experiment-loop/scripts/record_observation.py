#!/usr/bin/env python3
"""Append a short post-run data-walk observation to an experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state_lib import (
    TERMINAL_EXPERIMENT_STATUSES,
    append_jsonl,
    attribution_fields,
    experiment_records,
    latest_experiment_state,
    next_id,
    resolve_experiment_id,
    utc_now,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--experiment-id")
    parser.add_argument("--observation", action="append", default=[])
    parser.add_argument("--unexpected", action="store_true")
    parser.add_argument("--follow-up")
    parser.add_argument("--artifact-id", action="append", default=[])
    parser.add_argument("--created-by")
    args = parser.parse_args()

    if not args.observation:
        raise SystemExit("At least one --observation is required")
    if args.unexpected and not args.follow_up:
        raise SystemExit("An unexpected observation requires --follow-up")
    root = args.root.resolve()
    experiment_id = resolve_experiment_id(root, args.experiment_id)
    experiments, events = experiment_records(root)
    if latest_experiment_state(experiments[experiment_id], events).get("status") in TERMINAL_EXPERIMENT_STATUSES:
        raise SystemExit(f"Experiment is already terminal: {experiment_id}")
    registry = root / "research" / "experiments.jsonl"
    event = {
        "record_type": "experiment_event",
        "schema_version": 2,
        "id": next_id(registry, "EVT"),
        "experiment_id": experiment_id,
        "created_at": utc_now(),
        "event_type": "postrun_observation",
        "observations": args.observation,
        "unexpected": args.unexpected,
        "follow_up": args.follow_up,
        "artifacts": args.artifact_id,
    }
    event.update(attribution_fields(args.created_by))
    append_jsonl(registry, event)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
